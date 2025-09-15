# Multi‑Tenant MVP Plan

This plan breaks the migration into small, verifiable milestones with rollbacks and acceptance criteria. No app code changes occur until migrations and guardrails are ready.

## Assumptions
- Database: Postgres. ORM: SQLAlchemy. API: FastAPI. Frontend: Astro + Vue.
- Tests: pytest for backend, Vitest for UI.

## Milestones

### M0 — SQLite → Postgres Bootstrap & Data Migration
- Provision Postgres (version >= 14) and create target database and role(s).
- Run Alembic R1–R2 to create global tables (`tenants`, `tenant_memberships`, `invitations`).
- Export data from current SQLite DBs (admin, analytics, security) and import into Postgres staging tables.
- Transform and load into final tables, adding `tenant_id` (default tenant) where needed.
- Verify row counts, key integrity, and sample data parity; plan cutover window.

Acceptance
- Postgres contains equivalent data for all existing SQLite tables.
- Checksums/counts match per table; application can read from Postgres in read-only test mode.

Rollback
- Keep SQLite as canonical; if validation fails, discard PG data and fix scripts before retrying.

### M1 — Schema & Policies (foundation)
- Create core tables: `tenants`, `tenant_memberships`, `invitations`.
- Add `tenant_id` to tenant‑scoped domain tables; backfill to a seeded `DEFAULT_TENANT`.
- Add indexes and migrate uniques to composite `(tenant_id, ... )`.
- Enable RLS and add policies on all tenant‑scoped tables.

Notes
- For large tables, prefer creating indexes concurrently and then attaching them to constraints (Alembic supports non-transactional DDL blocks). Plan a brief maintenance window for unique swaps.

Acceptance
- Migrations run cleanly on dev DBs; new constraints enforced.
- RLS blocks cross‑tenant reads/writes using manual `SET LOCAL app.tenant_id` in psql.
- Coverage includes tests that prove RLS behavior at the DB level.

Rollback
- Disable RLS and drop policies; remove `tenant_id` columns if unrecoverable (only in dev).

### M2 — Backend Context & Session wiring
- Add middleware to resolve tenant from subdomain or `/:tenant` prefix (subdomain precedence; feature-flagged default tenant fallback).
- Introduce SQLAlchemy Engine/Session and per-request transaction; execute `SET LOCAL app.tenant_id = '<uuid>'` for every request.
- Option A (low churn): use SQLAlchemy Core with `text()` queries first; Option B: define ORM models and optionally add `with_loader_criteria` for defense in depth.
- Implement CRUD for tenants and memberships; simple invite flow scaffold (no email sending requirements beyond token generation).

Acceptance
- All existing domain endpoints operate with tenant context without code changes per handler.
- Cross‑tenant access attempts fail (403 or empty per route semantics).
- Logs include `tenant_id` for requests and DB queries.

Rollback
- Feature flag to bypass middleware and set default tenant; RLS remains enabled for safety.

Reference
- See `sqlalchemy_adoption_blueprint.md` for concrete wiring and rollout.

### M3 — Frontend Tenant Awareness
- Implement `useTenant()` composable: parse subdomain or `/:tenant` prefix, store in state.
- Add basic org switcher UI; support switching between at least two seeded tenants.
- Ensure API client does not depend on headers for security; backend resolution is canonical.

Acceptance
- Navigating between `/:tenant` prefixed routes switches context and data.
- Org switcher updates current tenant and view.

Rollback
- Hide switcher and lock UI to default tenant; backend still enforces RLS.

### M4 — Invitations & Membership Management (MVP)
- Create/accept invitation endpoints with simple token verification.
- Role checks on membership changes (`owner`/`admin` required to invite/remove).

Acceptance
- Users can create a tenant, invite another user, accept invite, and switch tenants.
- Permissions are enforced by role; DB prevents cross‑tenant leakage.

Rollback
- Disable invite endpoints; membership remains manageable by admins via DB in dev.

### M5 — Observability & Hardening
- Include `tenant_id` in structured logs and request IDs.
- Add per‑tenant request and error counters.
- Load test a few tenant‑heavy endpoints; validate indexes and slow query logs.

Acceptance
- Dashboards or logs make it easy to filter by `tenant_id`.
- No cross‑tenant leakage found in tests and manual checks.

## Deployment Strategy
- Ship migrations behind a maintenance window for schema changes.
- Deploy middleware behind a feature flag; start with default tenant for a subset of traffic.
- Incrementally enable multi‑tenant routing in staging before prod.

## Testing Strategy
- Unit tests for middleware and utilities.
- Integration tests for DB RLS behavior and endpoint scoping.
- E2E tests switching tenants and verifying isolated data.

## Out of Scope (for MVP)
- Billing and metering.
- Custom domains per tenant.
- SSO/SCIM.
- Data export/import per tenant.

## Risks & Mitigations
- Breaking uniques: audit all uniques and convert to composite in M1.
- Leaky queries: rely on RLS + ORM criteria and add linters/checks where possible.
- Connection pooling: ensure per‑request session context sets `SET LOCAL` for each transaction.
