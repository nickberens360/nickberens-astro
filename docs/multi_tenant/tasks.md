# Multi‑Tenant MVP Tasks

This is an actionable checklist to deliver the multi‑tenant MVP. Tasks are grouped by area with deliverables and acceptance criteria. Check off as completed.

## Legend
- [ ] open  | [x] done
- Area tags: [DB], [BE], [FE], [TEST], [OPS], [DOCS]

## 0. Prep & Decisions
- [ ] [DOCS] Confirm tenant identifier strategy (subdomain primary, `/:tenant` fallback).
- [ ] [OPS] Confirm Postgres version and extensions (UUID available) in all environments.
- [ ] [BE] Decide request logging format; include `tenant_id` and `request_id`.

## 1. Database & Migrations
- [ ] [DB] Create `tenants` table (id UUID PK, slug UNIQUE, name, timestamps, soft delete).
  - Deliverable: Alembic migration `xxxx_add_tenants.py`.
  - Acceptance: Can insert/read tenants; slug uniqueness enforced.
- [ ] [DB] Create `tenant_memberships` (tenant_id, user_id FK, role, timestamps).
  - Deliverable: migration `xxxx_add_tenant_memberships.py`.
  - Acceptance: Composite uniqueness `(tenant_id, user_id)` enforced.
- [ ] [DB] Create `invitations` (tenant_id, email, inviter_user_id, token UNIQUE, status, expires_at).
  - Deliverable: migration `xxxx_add_invitations.py`.
  - Acceptance: Unique token; FK constraints validate tenant relations.
- [ ] [DB] Add `tenant_id UUID NOT NULL` to tenant‑scoped domain tables.
  - Deliverable: migration `xxxx_add_tenant_id_domain_tables.py`.
  - Acceptance: Not null; indexes on `tenant_id`; composite uniques updated.
- [ ] [DB] Backfill `tenant_id` with seeded `DEFAULT_TENANT_ID` for existing rows.
  - Deliverable: data migration with safe batching if needed.
  - Acceptance: 100% rows have `tenant_id` set.
- [ ] [DB] Enable RLS and add policies for all tenant tables.
  - Deliverable: migration `xxxx_enable_rls_policies.py`.
  - Acceptance: Manual `SET LOCAL app.tenant_id` proves isolation in psql.

## 2. Backend — Tenant Context & Enforcement
- [ ] [BE] Middleware to resolve tenant (subdomain or `/:tenant`).
  - Deliverable: `backend/core/middleware/tenant.py`; tests.
  - Acceptance: `request.state.tenant_id` set; 404/400 for unknown tenants.
- [ ] [BE] DB session wrapper to set `SET LOCAL app.tenant_id` per request/transaction.
  - Deliverable: changes in `backend/core/db.py`; tests to assert `current_setting` visible.
  - Acceptance: RLS enforced without handler filtering.
- [ ] [BE] ORM defense‑in‑depth via `with_loader_criteria` for tenant‑scoped models.
  - Deliverable: session setup hook.
  - Acceptance: Queries without explicit filters still scoped.
- [ ] [BE] CRUD for tenants (create, rename, soft delete).
  - Deliverable: `backend/routes/tenants.py` + models.
  - Acceptance: Owner can manage; others blocked.
- [ ] [BE] Membership endpoints (list, add, remove, change role).
  - Deliverable: routes + validation.
  - Acceptance: Role checks enforced.
- [ ] [BE] Invitations endpoints (create, accept) with basic token issuance/verify.
  - Deliverable: routes + token util.
  - Acceptance: Invitee can join tenant; token expiry enforced.
- [ ] [BE] Update auth/JWT to include current membership (tenant_id, role) for convenience.
  - Deliverable: minimal JWT claim addition, optional.
  - Acceptance: Handlers can read role from token; DB still enforces isolation.

## 3. Frontend — Tenant Awareness
- [ ] [FE] `useTenant()` composable: parse subdomain or `/:tenant`, manage state, persist recent tenant.
  - Deliverable: `src/composables/useTenant.ts`.
  - Acceptance: Detects tenant across navigations; SSR‑friendly.
- [ ] [FE] Org switcher component in navbar.
  - Deliverable: `src/components/OrgSwitcher.vue`.
  - Acceptance: Lets user switch between at least two tenants; updates view.
- [ ] [FE] Update routes to support optional `/:tenant` prefix.
  - Deliverable: router config/docs.
  - Acceptance: Deep links with prefix render correctly.
- [ ] [FE] API client reads from `useTenant()`; avoid relying on headers for security.
  - Deliverable: minimal client wrapper tweak.
  - Acceptance: Works with both subdomain and prefix.

## 4. Testing
- [ ] [TEST] Unit tests: middleware tenant resolution edge cases.
- [ ] [TEST] Integration tests: RLS isolation for read/write across tenants.
- [ ] [TEST] E2E: create tenant, invite user, accept, switch tenant; verify isolation.
- [ ] [TEST] Performance: smoke test list endpoints with tenant index usage.

## 5. Observability & Ops
- [ ] [OPS] Include `tenant_id` in structured logs and tracing context.
- [ ] [OPS] Add per‑tenant metrics: request count, error count.
- [ ] [OPS] Seed script: create two tenants and test users for local dev.
- [ ] [OPS] Feature flag to toggle multi‑tenant routing on/off.
- [ ] [OPS] Deployment playbook: maintenance window for migrations; rollback notes.

## 6. Documentation
- [ ] [DOCS] Update README with multi‑tenant overview and local dev instructions (subdomain vs prefix).
- [ ] [DOCS] Add ERD and policy examples to `docs/multi_tenant/overview.md`.
- [ ] [DOCS] Record migration commands and manual validation steps.

## Reference Snippets (Policies)
```sql
-- Enable RLS
ALTER TABLE public.example ENABLE ROW LEVEL SECURITY;

-- Read/modify limited to current tenant
CREATE POLICY example_tenant_access ON public.example
  USING (tenant_id = current_setting('app.tenant_id')::uuid AND deleted_at IS NULL)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
```

## Manual Validation (Dev DB)
- Set context: `SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000001';`
- Verify visible rows all match the tenant.
- Switch tenant_id and confirm previous rows disappear and new tenant rows appear.

