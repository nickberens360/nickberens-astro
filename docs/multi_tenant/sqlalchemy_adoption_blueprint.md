# SQLAlchemy Adoption Blueprint (M2)

This blueprint outlines a pragmatic path to introduce SQLAlchemy and Postgres into the current backend (which primarily uses `sqlite3` and inline SQL) while enabling RLS-backed multi-tenancy. It aims to minimize churn and risk by layering SQLAlchemy alongside existing code, then gradually porting.

## Objectives
- Use Postgres with Row-Level Security (RLS) as the primary enforcement for tenant isolation.
- Ensure every request runs in a transaction that sets `SET LOCAL app.tenant_id`.
- Add SQLAlchemy Engine/Session and a per-request dependency without rewriting all routes at once.
- Provide a feature-flagged fallback to SQLite during migration/testing.

## Constraints and Current State
- Framework: FastAPI.
- Current data access: `sqlite3` connections and manager classes (e.g., admin database manager, query logger).
- Planned DB: Postgres 14+ with RLS.

## Phased Adoption

### Phase A — Introduce Engine + Session (no route rewrites)
- Add SQLAlchemy engine configured via `DATABASE_URL` (Postgres) and a feature flag to keep using SQLite in production until cutover.
- Create `SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)`. Avoid global sessions.
- Implement a FastAPI dependency that:
  - Opens a session at request start
  - Begins a transaction
  - Sets `SET LOCAL app.tenant_id = '<uuid>'` based on tenant resolved by middleware
  - Commits/rolls back and closes session after the response

Example per-request dependency:
```python
from contextlib import contextmanager
from sqlalchemy import event, text
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

def get_db_session(request: Request):
    session = SessionLocal()
    try:
        # Ensure a transaction is started so SET LOCAL applies
        session.execute(text("BEGIN"))
        tenant_id = request.state.tenant_id  # set by tenant middleware
        if tenant_id:
            session.execute(text("SET LOCAL app.tenant_id = :tid").bindparams(tid=str(tenant_id)))
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Notes
- Use `future=True` and explicit transactions. Do not rely on autocommit.
- The app DB role must be `NOBYPASSRLS`.

### Phase B — RLS-Aware Session Guarantees
- Verify via logs/tests that every request starts a transaction and sets `app.tenant_id`.
- Add safety checks:
  - If `tenant_id` is missing, either set to default tenant (behind feature flag) or abort with 400/403 depending on route.
  - Optionally add assertion checks in development to ensure `current_setting('app.tenant_id', true)` is set during critical queries.

### Phase C — Minimal Models and Gradual Porting
Pick a small set of tenant-scoped tables to model first (e.g., `admin_settings`, `followup_categories`, `followup_questions`).

Options for adoption:
- Low-churn: Use SQLAlchemy Core with textual SQL (`text()`) to replace `sqlite3` calls incrementally, leveraging the per-request Session and RLS. This avoids a full ORM model suite initially.
- ORM path: Define declarative models, add `tenant_id` columns, and use `with_loader_criteria` to add a defense-in-depth filter by `tenant_id`.

Example defense-in-depth (optional):
```python
from sqlalchemy.orm import with_loader_criteria

@contextmanager
def scoped_session_for_tenant(session, tenant_id):
    opts = session.execution_options()
    token = session.enable_relationship_loading
    try:
        session = session.execution_options(
            loader_criteria=[
                with_loader_criteria(TenantScopedBase, lambda cls: cls.tenant_id == tenant_id, include_aliases=True)
            ]
        )
        yield session
    finally:
        pass
```

Recommendation
- Start with SQLAlchemy Core + `text()` queries for the first few routes/managers to minimize complexity.
- Add ORM models later for domains that benefit from relationships and eager loading.

### Phase D — Feature Flags and Cutover
- Add flags to control:
  - Use Postgres driver vs. SQLite managers
  - Enable/disable tenant middleware
  - Fallback to default tenant in emergencies (RLS remains enabled)
- Cutover plan:
  - Staging: enable Postgres + RLS + middleware; run integration tests
  - Production: enable for a slice of traffic; monitor; roll forward

## Testing and Observability
- Integration tests:
  - Ensure `SET LOCAL app.tenant_id` is set on every request (inspect logs or a test-only endpoint).
  - Verify RLS blocks cross-tenant read/write with `psql` and via API.
- Logging:
  - Include `tenant_id` in structured logs and request IDs.
  - Log DB connection info (pool size) at startup.
- Metrics:
  - Add per-tenant request and error counters where feasible.

## Non-ORM Path (if deferring ORM)
- Keep existing `sqlite3` style but route those calls through a thin abstraction that:
  - Uses SQLAlchemy Engine/Session to execute SQL text in Postgres
  - Relies entirely on RLS for tenant isolation
- Pros: minimal rewrite; Cons: less type-safety and relationship handling.

## Rollback
- Toggle feature flags back to SQLite and disable tenant middleware. Keep RLS enabled on Postgres to prevent accidental exposure during rollback testing.

## Checklist
- [ ] Engine + Session wired with explicit transaction per request
- [ ] Tenant middleware sets `request.state.tenant_id`
- [ ] `SET LOCAL app.tenant_id` executed at request start
- [ ] App role `NOBYPASSRLS`, least-privilege grants
- [ ] First few routes/managers ported to SQLAlchemy Core or ORM
- [ ] Logs include `tenant_id`; tests cover cross-tenant denial

