# SQLite → Postgres Migration Playbook

This guide describes how to migrate existing data from multiple SQLite databases to a unified Postgres database as part of the multi‑tenant MVP. It complements `overview.md`, `plan.md` (M0), and `migrations_outline.md` (R1–R6).

## Why
- Consolidate multiple SQLite DBs into Postgres with a shared schema.
- Introduce tenant isolation using `tenant_id` and Row‑Level Security (RLS).
- Prepare the foundation for scalable multi‑tenant features.

## Sources and Targets

Current SQLite files used by the app (paths may vary slightly by env):
- Admin DB: `backend/logs/admin_monitoring.db`
- RAG Analytics DB: `backend/logs/rag_monitoring.db`
- Security Events: sometimes co‑located in Admin DB; may also exist as a dedicated SQLite file

Target (Postgres, schema `public`):
- Global: `tenants`, `tenant_memberships`, `invitations`, `users` (replaces `admin_users` semantics), `sessions`
- Tenant‑scoped: `admin_settings`, `taxonomy_settings_history`, `followup_categories`, `followup_questions`, `welcome_questions`, `api_keys`, `query_logs`, `content_gaps`, `security_events` (nullable `tenant_id` allowed)

Refer to `domain_inventory.md` for the definitive mapping of tables and uniques.

## Cutover Strategy
- Mode: Offline write freeze on SQLite during the final migration window; read‑only allowed until switchover.
- Plan: Dry‑run migration in staging; validate, then perform prod migration during a short maintenance window.
- Rollback: If validation fails, revert app to SQLite and discard PG load; investigate and retry.

## Prerequisites
- Postgres 14+ provisioned and reachable from dev/staging.
- Application role with least privilege created.
- `.env` prepared with new DSN (not used by app code until M2):
  - `DATABASE_URL=postgresql+psycopg://<user>:<pass>@<host>:<port>/<db>`
  - `DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001` (example)
- Recommended Postgres extensions:
  - `CREATE EXTENSION IF NOT EXISTS pgcrypto;` — for `gen_random_uuid()`

## Step 1 — Create Base Schema in Postgres
Follow `migrations_outline.md`:
- Run R1–R2 to create global tables: `tenants`, `tenant_memberships`, `invitations`.
- Run R3–R5 to prepare tenant‑scoped columns and indexes (RLS comes later in Step 6).

Notes
- If Alembic isn’t wired yet, apply equivalent DDL manually from the outlines.
- Seed a default tenant and persist its UUID for backfills:
  - `INSERT INTO tenants (id, slug, name) VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'Default Tenant') ON CONFLICT DO NOTHING;`

## Step 2 — Create Staging Area
Use a dedicated staging schema to ingest raw CSVs from SQLite.

```sql
CREATE SCHEMA IF NOT EXISTS stg;
-- Example staging tables (minimal typing; adjust as needed)
CREATE TABLE IF NOT EXISTS stg.admin_users (
  id BIGINT, username TEXT, email TEXT, password_hash TEXT,
  role TEXT, is_active BOOLEAN, created_at TEXT, last_login_at TEXT, updated_at TEXT, display_name TEXT
);
CREATE TABLE IF NOT EXISTS stg.admin_settings (
  id BIGINT, setting_key TEXT, setting_value TEXT, updated_at TEXT, updated_by TEXT
);
CREATE TABLE IF NOT EXISTS stg.followup_categories (
  id BIGINT, name TEXT, display_name TEXT, description TEXT, icon TEXT,
  sort_order BIGINT, is_active BIGINT, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS stg.followup_questions (
  id BIGINT, category_id BIGINT, question_text TEXT,
  sort_order BIGINT, is_active BIGINT, created_at TEXT, updated_at TEXT, created_by TEXT
);
CREATE TABLE IF NOT EXISTS stg.welcome_questions (
  id BIGINT, question_text TEXT, sort_order BIGINT, is_active BIGINT, created_at TEXT, updated_at TEXT, created_by TEXT
);
CREATE TABLE IF NOT EXISTS stg.api_keys (
  id BIGINT, key_name TEXT, key_type TEXT, encrypted_value TEXT, last_four TEXT,
  is_active BIGINT, last_used_at TEXT, last_validated_at TEXT, created_at TEXT, updated_at TEXT, updated_by TEXT
);
CREATE TABLE IF NOT EXISTS stg.query_logs (
  id BIGINT, session_id TEXT, request_id TEXT, user_query TEXT, system_response TEXT,
  query_type TEXT, response_time_ms REAL, llm_provider TEXT, llm_model TEXT,
  vector_search_score REAL, sources_used TEXT, follow_up_questions TEXT,
  cache_hit BIGINT, error_occurred BIGINT, error_message TEXT, user_feedback TEXT,
  timestamp TEXT, client_ip TEXT, location_city TEXT, location_region TEXT,
  location_country TEXT, location_country_code TEXT
);
CREATE TABLE IF NOT EXISTS stg.content_gaps (
  id BIGINT, query_pattern TEXT, occurrence_count BIGINT, avg_similarity_score REAL,
  first_seen TEXT, last_seen TEXT, resolved BIGINT, notes TEXT, sample_query_id BIGINT
);
CREATE TABLE IF NOT EXISTS stg.security_events (
  id BIGINT, event_type TEXT, identifier TEXT, details TEXT, severity TEXT,
  ip_address TEXT, user_agent TEXT, created_at TEXT
);
```

## Step 3 — Export From SQLite to CSV
Use `sqlite3` to export data per table. Example for Admin DB:

```bash
sqlite3 backend/logs/admin_monitoring.db <<'SQL'
.headers on
.mode csv
.once admin_users.csv
SELECT * FROM admin_users;
.once admin_settings.csv
SELECT * FROM admin_settings;
.once followup_categories.csv
SELECT * FROM followup_categories;
.once followup_questions.csv
SELECT * FROM followup_questions;
.once welcome_questions.csv
SELECT * FROM welcome_questions;
.once api_keys.csv
SELECT * FROM api_keys;
SQL

sqlite3 backend/logs/rag_monitoring.db <<'SQL'
.headers on
.mode csv
.once query_logs.csv
SELECT * FROM query_logs;
.once content_gaps.csv
SELECT * FROM content_gaps;
SQL
```

Optional: Use `pgloader` to automate (if available). A simple pgloader command can map SQLite → Postgres directly for staging.

## Step 4 — Load CSVs Into Staging

```bash
psql "$DATABASE_URL" -c "\COPY stg.admin_users FROM 'admin_users.csv' WITH (FORMAT csv, HEADER true)"
psql "$DATABASE_URL" -c "\COPY stg.admin_settings FROM 'admin_settings.csv' WITH (FORMAT csv, HEADER true)"
psql "$DATABASE_URL" -c "\COPY stg.followup_categories FROM 'followup_categories.csv' WITH (FORMAT csv, HEADER true)"
psql "$DATABASE_URL" -c "\COPY stg.followup_questions FROM 'followup_questions.csv' WITH (FORMAT csv, HEADER true)"
psql "$DATABASE_URL" -c "\COPY stg.welcome_questions FROM 'welcome_questions.csv' WITH (FORMAT csv, HEADER true)"
psql "$DATABASE_URL" -c "\COPY stg.api_keys FROM 'api_keys.csv' WITH (FORMAT csv, HEADER true)"
psql "$DATABASE_URL" -c "\COPY stg.query_logs FROM 'query_logs.csv' WITH (FORMAT csv, HEADER true)"
psql "$DATABASE_URL" -c "\COPY stg.content_gaps FROM 'content_gaps.csv' WITH (FORMAT csv, HEADER true)"
# If separate
# psql "$DATABASE_URL" -c "\COPY stg.security_events FROM 'security_events.csv' WITH (FORMAT csv, HEADER true)"
```

## Step 5 — Transform and Load Into Final Tables

Set a default tenant UUID (must match the seeded `tenants.id`). Replace with your real value.

```sql
-- Substitute with your chosen default tenant
\set default_tenant '00000000-0000-0000-0000-000000000001'

-- users (from admin_users). If you already have a global users table, adjust columns accordingly.
INSERT INTO users (id, username, email, password_hash, role, is_active, created_at, last_login_at, updated_at, display_name)
SELECT id, username, email, password_hash, role,
       COALESCE(is_active::boolean, true),
       NULLIF(created_at, '')::timestamptz,
       NULLIF(last_login_at, '')::timestamptz,
       NULLIF(updated_at, '')::timestamptz,
       display_name
FROM stg.admin_users
ON CONFLICT (id) DO NOTHING;

-- admin_settings → tenant‑scoped
INSERT INTO admin_settings (id, tenant_id, setting_key, setting_value, updated_at, updated_by)
SELECT s.id, :'default_tenant'::uuid, s.setting_key, s.setting_value,
       NULLIF(s.updated_at, '')::timestamptz, s.updated_by
FROM stg.admin_settings s
ON CONFLICT (id) DO NOTHING;

-- followup_categories → tenant‑scoped
INSERT INTO followup_categories (id, tenant_id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at)
SELECT c.id, :'default_tenant'::uuid, c.name, c.display_name, c.description, c.icon,
       NULLIF(c.sort_order::text, '')::int,
       COALESCE((c.is_active = 1), true),
       NULLIF(c.created_at, '')::timestamptz,
       NULLIF(c.updated_at, '')::timestamptz
FROM stg.followup_categories c
ON CONFLICT (id) DO NOTHING;

-- followup_questions → tenant‑scoped (assumes FK to followup_categories.id within same tenant)
INSERT INTO followup_questions (id, tenant_id, category_id, question_text, sort_order, is_active, created_at, updated_at, created_by)
SELECT q.id, :'default_tenant'::uuid, q.category_id, q.question_text,
       NULLIF(q.sort_order::text, '')::int,
       COALESCE((q.is_active = 1), true),
       NULLIF(q.created_at, '')::timestamptz,
       NULLIF(q.updated_at, '')::timestamptz,
       q.created_by
FROM stg.followup_questions q
ON CONFLICT (id) DO NOTHING;

-- welcome_questions → tenant‑scoped
INSERT INTO welcome_questions (id, tenant_id, question_text, sort_order, is_active, created_at, updated_at)
SELECT w.id, :'default_tenant'::uuid, w.question_text,
       NULLIF(w.sort_order::text, '')::int,
       COALESCE((w.is_active = 1), true),
       NULLIF(w.created_at, '')::timestamptz,
       NULLIF(w.updated_at, '')::timestamptz
FROM stg.welcome_questions w
ON CONFLICT (id) DO NOTHING;

-- api_keys → tenant‑scoped
INSERT INTO api_keys (id, tenant_id, key_name, key_type, encrypted_value, last_four, is_active, last_used_at, last_validated_at, created_at, updated_at, updated_by)
SELECT a.id, :'default_tenant'::uuid, a.key_name, a.key_type, a.encrypted_value, a.last_four,
       COALESCE((a.is_active = 1), true),
       NULLIF(a.last_used_at, '')::timestamptz,
       NULLIF(a.last_validated_at, '')::timestamptz,
       NULLIF(a.created_at, '')::timestamptz,
       NULLIF(a.updated_at, '')::timestamptz,
       a.updated_by
FROM stg.api_keys a
ON CONFLICT (id) DO NOTHING;

-- query_logs → tenant‑scoped
INSERT INTO query_logs (
  id, tenant_id, session_id, request_id, user_query, system_response, query_type,
  response_time_ms, llm_provider, llm_model, vector_search_score, sources_used,
  follow_up_questions, cache_hit, error_occurred, error_message, user_feedback,
  timestamp, client_ip, location_city, location_region, location_country, location_country_code
)
SELECT q.id, :'default_tenant'::uuid, q.session_id, q.request_id, q.user_query, q.system_response, COALESCE(NULLIF(q.query_type, ''), 'text'),
       q.response_time_ms, q.llm_provider, q.llm_model, q.vector_search_score,
       NULLIF(q.sources_used, '')::jsonb, NULLIF(q.follow_up_questions, '')::jsonb,
       (q.cache_hit = 1), (q.error_occurred = 1), q.error_message, q.user_feedback,
       NULLIF(q.timestamp, '')::timestamptz, q.client_ip, q.location_city, q.location_region, q.location_country, q.location_country_code
FROM stg.query_logs q
ON CONFLICT (id) DO NOTHING;

-- content_gaps → tenant‑scoped (ensure sample_query_id refers to same tenant row)
INSERT INTO content_gaps (
  id, tenant_id, query_pattern, occurrence_count, avg_similarity_score,
  first_seen, last_seen, resolved, notes, sample_query_id
)
SELECT g.id, :'default_tenant'::uuid, g.query_pattern,
       NULLIF(g.occurrence_count::text, '')::int,
       g.avg_similarity_score,
       NULLIF(g.first_seen, '')::timestamptz,
       NULLIF(g.last_seen, '')::timestamptz,
       (g.resolved = 1), g.notes, g.sample_query_id
FROM stg.content_gaps g
ON CONFLICT (id) DO NOTHING;

-- security_events (nullable tenant_id acceptable if events are infra‑level)
INSERT INTO security_events (
  id, tenant_id, event_type, identifier, details, severity, ip_address, user_agent, created_at
)
SELECT s.id, :'default_tenant'::uuid, s.event_type, s.identifier, s.details, s.severity, s.ip_address, s.user_agent,
       NULLIF(s.created_at, '')::timestamptz
FROM stg.security_events s
ON CONFLICT (id) DO NOTHING;
```

Notes
- Adjust casts if your staging columns differ.
- If any JSON was stored as TEXT in SQLite, ensure it’s valid before casting to `jsonb`.
- If duplicates violate new composite uniques, de‑duplicate in staging first.

## Step 6 — Enable RLS and Policies
After all data is loaded and validated, enable RLS (R6) per `migrations_outline.md`.

Important
- Apply policies only after inserts complete, or insert using a role with permission to bypass RLS.
- Runtime access will set `SET LOCAL app.tenant_id = '<uuid>'` per request.

## Step 7 — Sequence/Identity Fix‑ups
If any tables use identity/serial columns and you inserted explicit `id` values, reset sequences:

```sql
SELECT setval(pg_get_serial_sequence('followup_categories', 'id'), COALESCE((SELECT MAX(id) FROM followup_categories), 1));
SELECT setval(pg_get_serial_sequence('followup_questions', 'id'), COALESCE((SELECT MAX(id) FROM followup_questions), 1));
-- Repeat as needed for other integer PKs
```

## Step 8 — Validation

Counts
```sql
-- Compare staging vs final counts quickly
SELECT 'admin_settings' AS table, (SELECT COUNT(*) FROM stg.admin_settings) AS stg, (SELECT COUNT(*) FROM admin_settings) AS final
UNION ALL
SELECT 'followup_categories', (SELECT COUNT(*) FROM stg.followup_categories), (SELECT COUNT(*) FROM followup_categories)
UNION ALL
SELECT 'followup_questions', (SELECT COUNT(*) FROM stg.followup_questions), (SELECT COUNT(*) FROM followup_questions)
UNION ALL
SELECT 'welcome_questions', (SELECT COUNT(*) FROM stg.welcome_questions), (SELECT COUNT(*) FROM welcome_questions)
UNION ALL
SELECT 'api_keys', (SELECT COUNT(*) FROM stg.api_keys), (SELECT COUNT(*) FROM api_keys)
UNION ALL
SELECT 'query_logs', (SELECT COUNT(*) FROM stg.query_logs), (SELECT COUNT(*) FROM query_logs)
UNION ALL
SELECT 'content_gaps', (SELECT COUNT(*) FROM stg.content_gaps), (SELECT COUNT(*) FROM content_gaps)
UNION ALL
SELECT 'security_events', (SELECT COUNT(*) FROM stg.security_events), (SELECT COUNT(*) FROM security_events);
```

Spot‑checks
```sql
-- Verify JSON cast worked and arrays look sane
SELECT id, jsonb_typeof(sources_used) AS sources_t, jsonb_typeof(follow_up_questions) AS fuq_t
FROM query_logs WHERE sources_used IS NOT NULL OR follow_up_questions IS NOT NULL LIMIT 20;

-- Verify tenant scoping
SET LOCAL app.tenant_id = :'default_tenant';
SELECT COUNT(*) FROM query_logs; -- should match final count for default tenant
```

## Step 9 — Cutover
- Keep SQLite as canonical until backend (M2) uses Postgres connections.
- Switch app to Postgres when M2 is complete:
  - Update `.env` to include `DATABASE_URL` (and feature flag to enable PG driver)
  - Deploy backend with middleware/session wiring that sets `app.tenant_id`
- Monitor metrics and logs with `tenant_id` context; be ready to rollback.

## Gotchas & Tips
- Timestamps: Normalize to UTC; cast SQLite `TEXT` timestamps with `::timestamptz`.
- Booleans: In SQLite 0/1 often stored as INTEGER; cast to boolean in SELECT.
- Collation: Postgres text sorting differs from SQLite; be explicit in queries if ordering matters.
- Uniques: Before switching to composite uniques, check for duplicates in staging; resolve conflicts deterministically.
- FKs across tenant tables: Ensure `tenant_id` matches on both sides; enforce via RLS `WITH CHECK`.
- Performance: Use `\COPY` for bulk loads; create indexes after big inserts where possible.

## Rollback
- If validation or smoke tests fail, stop the app, point it back to SQLite, drop/empty the Postgres target tables or staging schema, fix issues, and retry.
- Keep CSV exports for quick re‑ingest.

## References
- Plan (M0): `docs/multi_tenant/plan.md`
- Migration Outlines (R1–R6): `docs/multi_tenant/migrations_outline.md`
- Domain Inventory: `docs/multi_tenant/domain_inventory.md`

