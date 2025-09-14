# Multi‑Tenant Tasks

This is the actionable task list to deliver the Multi‑Tenant MVP. It aligns with the overview, plan, and migration outlines in this folder. Tasks are grouped by phase and discipline, with clear acceptance criteria and notes.

## Scope
- In scope (MVP): shared‑schema Postgres, `tenant_id` scoping + RLS, tenant resolution middleware, minimal org switcher, basic invitations, data migration from SQLite, observability.
- Out of scope: billing/SSO/custom domains/SCIM, hard multi‑db sharding, per‑tenant migrations.

## Legend
- [ ] Todo
- [~] In Progress
- [x] Done

## Phase Summary (M0–M5)
- M0: Bootstrap Postgres + migrate data from SQLite
- M1: Schema changes + RLS policies
- M2: Backend tenant context + session wiring
- M3: Frontend tenant awareness + org switcher
- M4: Invitations + membership management
- M5: Observability + hardening

---

## M0 — SQLite → Postgres Bootstrap & Data Migration

- [ ] Provision Postgres (>=14), create DB/role with least privilege
  - Acceptance: App role created, can connect from dev/staging
  - Notes: Prepare `.env` with `DATABASE_URL=postgresql+psycopg://...`

- [ ] Create base schema in Postgres (run Alembic R1–R2)
  - Acceptance: `tenants`, `tenant_memberships`, `invitations` exist
  - Notes: Do not enable RLS yet; that happens in M1/R6

- [ ] Inventory SQLite sources and target mapping
  - Acceptance: Tables cataloged per `domain_inventory.md`; final table names agreed
  - Notes: Admin DB, RAG analytics DB, Security events DB

- [ ] Export SQLite data to CSV (or use pgloader) into staging tables
  - Acceptance: Staging tables populated in Postgres with raw rows
  - Notes: Follow `sqlite_to_postgres_migration.md` recipes

- [ ] Transform + load into final tables with default `tenant_id`
  - Acceptance: Final tenant‑scoped tables populated; row counts match within tolerance
  - Notes: Handle booleans, timestamps (UTC), JSON/text fields safely

- [ ] Validate and sign‑off
  - Acceptance: Row counts and sample hashes match; basic read path via app is green in staging
  - Rollback: Switch app back to SQLite; discard PG data and retry

---

## M1 — Schema & RLS Policies

- [ ] Add `tenant_id` to tenant‑scoped tables (nullable → backfill → not null)
  - Acceptance: Columns added; backfilled with default tenant; constraints pass

- [ ] Convert uniques to composite with `tenant_id`
  - Acceptance: Uniques migrated; DDL locks planned in a window

- [ ] Create indexes for `tenant_id` and hot filters
  - Acceptance: Explain plans show index usage on `(tenant_id, timestamp)` etc.

- [ ] Enable RLS and create policies per pattern
  - Acceptance: RLS blocks cross‑tenant access in psql with `SET LOCAL app.tenant_id`

- [ ] Add soft‑delete `deleted_at` where beneficial
  - Acceptance: Policies reference `deleted_at IS NULL` consistently

---

## M2 — Backend Tenant Context & Session Wiring

- [ ] Tenant resolution middleware (subdomain, or `/:tenant` dev fallback)
  - Acceptance: Request carries `request.state.tenant_id` for all routes

- [ ] DB session wrapper sets `SET LOCAL app.tenant_id = '<uuid>'`
  - Acceptance: Queries run under correct tenant; RLS enforced without per‑query filters

- [ ] Defense‑in‑depth ORM scoping (`with_loader_criteria`)
  - Acceptance: Critical ORM models scoped by default to `tenant_id`

- [ ] CRUD for tenants + memberships
  - Acceptance: Create tenant, add/remove member, list user’s tenants

- [ ] Feature flag to temporarily pin to default tenant
  - Acceptance: Safe bypass for emergency rollback while RLS stays enabled

---

## M3 — Frontend Tenant Awareness

- [ ] `useTenant()` composable to resolve current tenant (subdomain/prefix)
  - Acceptance: Composable returns `tenantId`, updates on route change

- [ ] Minimal org switcher UI in navbar
  - Acceptance: Switching updates route/context; no page reload required

- [ ] Route conventions support `/:tenant/...` in dev
  - Acceptance: Deep links work with tenant prefix in Astro/Vue router

---

## M4 — Invitations & Memberships (MVP)

- [ ] Issue/accept invitation endpoints with signed tokens
  - Acceptance: User B can accept invite from User A’s tenant; idempotent

- [ ] Role checks on membership changes
  - Acceptance: Only `owner`/`admin` can invite/remove; 403 otherwise

- [ ] Basic UI for invite flow (copy link)
  - Acceptance: Happy path covered; email sending optional

---

## M5 — Observability & Hardening

- [ ] Include `tenant_id` in structured logs + request IDs
  - Acceptance: Logs filterable by `tenant_id`

- [ ] Per‑tenant metrics (requests, errors)
  - Acceptance: Counters visible in dashboards/logs

- [ ] Load test hot paths; verify indexes
  - Acceptance: P95/P99 acceptable; slow queries tracked and fixed

---

## Cross‑Cutting Tasks

- [ ] Update `.env.example` and config loader
  - Add `DATABASE_URL`, `DEFAULT_TENANT_ID`, and feature flags

- [ ] Update CI to spin Postgres for tests (services: postgres)
  - Acceptance: `pytest -q` runs against ephemeral Postgres

- [ ] Write integration tests for RLS and tenant routing
  - Acceptance: Cross‑tenant attempts fail; same‑tenant succeed

- [ ] Data privacy review for logs/analytics
  - Acceptance: Logging excludes or anonymizes sensitive data per tenant

- [ ] Operational runbooks (backup/restore, seed, smoke tests)
  - Acceptance: Docs captured in `/docs/multi_tenant` and `/docs/operational`

---

## References
- Overview: `docs/multi_tenant/overview.md`
- Plan: `docs/multi_tenant/plan.md`
- Migration outlines (Alembic): `docs/multi_tenant/migrations_outline.md`
- SQLite → Postgres playbook: `docs/multi_tenant/sqlite_to_postgres_migration.md`

