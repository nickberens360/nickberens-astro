# SQLite → Postgres Migration Plan

This guide describes how to migrate the project’s data from multiple SQLite databases to a single Postgres database as part of the multi‑tenant MVP. No app code changes are required to perform this migration; it uses schema migrations plus ETL scripts/tools.

## Overview
- Sources
  - Admin DB: `admin_monitoring.db` (users, sessions, settings, api_keys, followup_*, welcome_questions, rate_limiting, security_events, etc.)
  - Analytics DB: `rag_monitoring.db` (query_logs, content_gaps)
  - Security DB: `security_events.db` (security_events)
- Target: Postgres (single DB, shared schema `public`) with new multi‑tenant schema.
- Strategy
  1) Create Postgres schema via Alembic (R1–R2 first; R3–R6 after data load).
  2) Extract from SQLite → Stage in Postgres → Transform → Load to final tables.
  3) Validate counts and keys; schedule cutover.

## Prerequisites
- Postgres 14+ and `psql` available.
- Optional tools: `pgloader` (best for bulk SQLite→PG), or Python ETL using `sqlite3` + `psycopg2`/SQLAlchemy + `COPY`.
- Connection: `DATABASE_URL=postgresql://user:pass@host:5432/yourdb`
- Decide `DEFAULT_TENANT_ID` to backfill tenant_id during migration (stable UUID).

## High-Level Steps
1) Provision Postgres and create DB/role(s).
2) Run Alembic revisions R1–R2
   - R1: `tenants`
   - R2: `tenant_memberships`, `invitations`
   - Seed the default tenant row with `DEFAULT_TENANT_ID` and slug `default`.
3) Create staging tables mirroring SQLite schemas (no `tenant_id` yet), e.g., `stg_admin_users`, `stg_query_logs`, etc.
4) Bulk-load data from SQLite into staging tables.
5) Transform + load into final tables, adding `tenant_id = DEFAULT_TENANT_ID` where tenant-scoped.
6) Add indexes/uniques and enable RLS (R3–R6) after data has landed.
7) Validate and cut over.

## Table Mapping Summary
- admin_users → users (global)
- admin_sessions → sessions (global; add `current_tenant_id` nullable later)
- admin_settings → admin_settings (tenant; add `tenant_id`)
- taxonomy_settings_history → taxonomy_settings_history (tenant)
- rate_limiting → rate_limiting (global; optional `tenant_id` later)
- security_events (either DB) → security_events (tenant preferred; can be nullable)
- user_2fa → user_2fa (global)
- followup_categories → followup_categories (tenant)
- followup_questions → followup_questions (tenant)
- welcome_questions → welcome_questions (tenant)
- api_keys → api_keys (tenant)
- query_logs → query_logs (tenant)
- content_gaps → content_gaps (tenant)

Refer to `docs/multi_tenant/domain_inventory.md` for precise scoping and unique constraints.

## Option A: pgloader (fast path)
pgloader can read from SQLite files and write into Postgres, handling basic type mapping.

- Install: `brew install pgloader` (macOS) or use a container.
- Example pgloader script (edit paths/connection):

```lisp
LOAD DATABASE
     FROM sqlite:///absolute/path/to/admin_monitoring.db
     INTO postgresql://user:pass@host:5432/yourdb

  WITH include drop, create no tables, batch rows = 5000

  SET work_mem to '128MB', maintenance_work_mem to '512 MB';

  CAST type datetime to timestamptz using current_timestamp;
```

Notes
- Use separate runs for each SQLite DB (admin, analytics, security) into staging tables (`stg_*`).
- Prefer “create no tables” if Alembic manages final tables; allow pgloader to create `stg_*` tables via a prior script or use `--with create tables` into a dedicated `staging` schema.

## Option B: Python ETL + COPY (portable)
- Use Python to read from SQLite and stream CSV to Postgres via `COPY` (fast and controllable).
- Pseudocode outline:

```python
# read SQLite in chunks
import sqlite3, csv, io
import psycopg2

src = sqlite3.connect('backend/logs/admin_monitoring.db')
pg = psycopg2.connect(os.environ['DATABASE_URL'])

cur = src.cursor(); pcur = pg.cursor()

# 1) create staging table
pcur.execute('CREATE TABLE IF NOT EXISTS stg_admin_users (id bigint, username text, email text, password_hash text, role text, is_active bool, created_at timestamptz, last_login_at timestamptz, updated_at timestamptz)')

# 2) export from sqlite
cur.execute('SELECT id, username, email, password_hash, role, is_active, created_at, last_login_at, updated_at FROM admin_users')
rows = cur.fetchall()

# 3) COPY into Postgres
buf = io.StringIO()
w = csv.writer(buf)
for r in rows:
    w.writerow(r)
buf.seek(0)
pcur.copy_expert('COPY stg_admin_users FROM STDIN WITH CSV', buf)
pg.commit()
```

Repeat per table and per SQLite DB.

## Transform and Load into Final Tables
After staging load completes:

- Users
```sql
INSERT INTO users (id, username, email, password_hash, role, is_active, created_at, last_login_at, updated_at)
SELECT id, username, email, password_hash, role, is_active, created_at, last_login_at, updated_at
FROM stg_admin_users
ON CONFLICT (id) DO NOTHING;
```

- Tenant-scoped tables (example: admin_settings)
```sql
INSERT INTO admin_settings (tenant_id, setting_key, setting_value, updated_at)
SELECT :'DEFAULT_TENANT_ID'::uuid, setting_key, setting_value, updated_at
FROM stg_admin_settings;
```

- Query analytics (query_logs)
```sql
INSERT INTO query_logs (
  tenant_id, user_query, system_response, query_type, response_time_ms,
  llm_provider, llm_model, vector_search_score, sources_used, follow_up_questions,
  cache_hit, error_occurred, error_message, client_ip, timestamp
)
SELECT :'DEFAULT_TENANT_ID'::uuid, user_query, system_response, COALESCE(query_type,'text'),
       response_time_ms, llm_provider, llm_model, vector_search_score, sources_used,
       follow_up_questions, cache_hit, error_occurred, error_message, client_ip, timestamp
FROM stg_query_logs;
```

- Content gaps (FK to query_logs)
```sql
INSERT INTO content_gaps (
  tenant_id, query_pattern, occurrence_count, avg_similarity_score, first_seen, last_seen, resolved, notes, sample_query_id
)
SELECT :'DEFAULT_TENANT_ID'::uuid, query_pattern, occurrence_count, avg_similarity_score, first_seen, last_seen, resolved, notes, sample_query_id
FROM stg_content_gaps;
```

- Security events
```sql
INSERT INTO security_events (
  tenant_id, event_type, identifier, details, severity, ip_address, user_agent, created_at
)
SELECT NULL::uuid, event_type, identifier, details, severity, ip_address, user_agent, created_at
FROM stg_security_events;
```

Adjust per table; see `domain_inventory.md` for scoping.

## Type Mapping Notes
- SQLite `INTEGER` → `bigint` or `integer` depending on ID size.
- SQLite `TEXT` → `text` or `varchar(n)` as needed.
- Dates/times → `timestamptz`.
- Booleans: SQLite uses 0/1; cast to `boolean` in Postgres.
- JSON fields stored as TEXT can remain text for MVP; consider `jsonb` later.

## Order of Operations
1) Create global tables (R1–R2) and staging tables.
2) Load staging from SQLite (admin → stg_, analytics → stg_, security → stg_).
3) Load global targets first (`users`) then tenant‑scoped with `tenant_id` default.
4) Add indexes/uniques and enable RLS (R3–R6) after verify.

## Validation Checklist
- Row counts equal per table (allowing expected differences, e.g., filtered abandoned rows).
- Key integrity: no NULLs on NOT NULL columns.
- Sample queries return identical payloads.
- Composite uniques valid; no conflicts.

Example count checks
```sql
SELECT 'users', COUNT(*) FROM users;
SELECT 'admin_settings', COUNT(*) FROM admin_settings;
SELECT 'query_logs', COUNT(*) FROM query_logs;
```

## Cutover Plan
- Freeze writes to SQLite (put app in maintenance or read‑only mode).
- Run final incremental export of rows created since initial dump (by timestamp), load to Postgres.
- Point the app to Postgres (feature flag/env switch) in staging, run smoke tests.
- Promote to production; keep SQLite read‑only backup for rollback window.

## Rollback Plan
- If validation fails, switch app back to SQLite, diagnose differences, and rerun ETL.
- Keep dated snapshots of SQLite files for audit.

## Post‑Migration Steps
- Enable RLS and policies (R6).
- Monitor performance and add missing indexes.
- Decommission SQLite usage after verification window.

---

Appendix: Staging Table Templates
- Create staging tables with columns mirroring SQLite schema exactly.
- Prefer a dedicated `staging` schema to avoid name clashes: `CREATE SCHEMA IF NOT EXISTS staging;` and prefix tables as `staging.admin_users`.
- Drop staging after successful load and verification.

