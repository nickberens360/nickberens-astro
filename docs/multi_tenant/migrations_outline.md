# Alembic Migration Outlines — Multi‑Tenant MVP

This document specifies the sequence and contents of Alembic revisions to introduce multi‑tenancy with Postgres Row‑Level Security (RLS). It is implementation‑ready guidance; no code changes are made here.

## Summary & Sequencing
- R1: Create `tenants` table and seed default tenant
- R2: Create `tenant_memberships` and `invitations`
- R3: Add `tenant_id` columns to tenant‑scoped domain tables
- R4: Backfill `tenant_id` with default tenant for existing rows
- R5: Indexes and composite unique constraints including `tenant_id`
- R6: Enable RLS and add policies for all tenant tables

Each revision should be independently reversible via `downgrade()`.

## Conventions & Assumptions
- DB: Postgres; schema `public`.
- GUC for RLS: `app.tenant_id` (UUID string). Set per transaction via `SET LOCAL app.tenant_id = '<uuid>'`.
- Soft‑delete: `deleted_at TIMESTAMPTZ NULL` on tenant‑scoped tables recommended.
- Default tenant ID: use an env var `DEFAULT_TENANT_ID` when seeding, or generate a stable UUID in the migration.
- Constraint names: use explicit names to avoid dialect‑generated names that vary by env.
- Large tables: avoid table rewrites; add columns NULL first, backfill, then set NOT NULL.

## Inventory Step (pre‑work)
Identify tenant‑scoped tables. For each, list:
- Table name
- Primary key
- Current unique constraints/indexes to be converted to composite with `tenant_id`

Example placeholder list to replace in R3–R6:
- `projects(name UNIQUE)` -> becomes UNIQUE(`tenant_id`, `name`)
- `tasks(uid UNIQUE)` -> becomes UNIQUE(`tenant_id`, `uid`)

## R1 — Create `tenants`
Example Alembic revision skeleton (fill in `revision` and `down_revision`):

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "r1_create_tenants"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # Optional seed default tenant
    # default_id = sa.text("'00000000-0000-0000-0000-000000000001'::uuid")  # or read from env in offline mode
    # op.execute(sa.text("INSERT INTO tenants (id, slug, name) VALUES (:id, :slug, :name) ON CONFLICT DO NOTHING").bindparams(
    #     id=default_id, slug="default", name="Default Tenant"
    # ))


def downgrade():
    op.drop_table("tenants")
```

Notes
- If you seed a default tenant here, persist the chosen UUID for later backfills.

## R2 — Create `tenant_memberships` and `invitations`
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "r2_memberships_invitations"
down_revision = "r1_create_tenants"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),  # FK to users table if available
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_membership_tenant_user", "tenant_memberships", ["tenant_id", "user_id"])

    op.create_table(
        "invitations",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("inviter_user_id", sa.BigInteger, nullable=False),  # FK optional
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_invitations_token", "invitations", ["token"], unique=True)


def downgrade():
    op.drop_index("ix_invitations_token", table_name="invitations")
    op.drop_table("invitations")
    op.drop_constraint("uq_membership_tenant_user", "tenant_memberships", type_="unique")
    op.drop_table("tenant_memberships")
```

Notes
- Replace `user_id` with the correct FK once the users table is confirmed.

## R3 — Add `tenant_id` to domain tables (NULLable first)
Pattern for each tenant‑scoped table:

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "r3_add_tenant_id_columns"
down_revision = "r2_memberships_invitations"

TENANT_TABLES = [
    # (table_name, column_type, index_name)
    ("projects", postgresql.UUID(as_uuid=True), "ix_projects_tenant_id"),
    ("tasks", postgresql.UUID(as_uuid=True), "ix_tasks_tenant_id"),
    # add more
]

def upgrade():
    for table, coltype, ix in TENANT_TABLES:
        op.add_column(table, sa.Column("tenant_id", coltype, nullable=True))  # NULL first to avoid rewrite
        op.create_index(ix, table, ["tenant_id"], unique=False)


def downgrade():
    # drop in reverse order
    for table, _, ix in reversed(TENANT_TABLES):
        op.drop_index(ix, table_name=table)
        op.drop_column(table, "tenant_id")
```

Notes
- Avoid `server_default` on `UUID()` here to prevent whole‑table rewrites.

## R4 — Backfill `tenant_id`
Perform a safe backfill to a known default tenant. For large tables, consider batching.

```python
from alembic import op
from sqlalchemy.sql import text

revision = "r4_backfill_tenant_id"
down_revision = "r3_add_tenant_id_columns"

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"  # replace or inject via env/config

TABLES = [
    "projects",
    "tasks",
    # add more
]

def upgrade():
    for table in TABLES:
        op.execute(text(f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL").bindparams(tid=DEFAULT_TENANT_ID))
    # Set NOT NULL after backfill
    for table in TABLES:
        op.alter_column(table, "tenant_id", nullable=False)


def downgrade():
    # Allow NULL again (optional), then clear values
    for table in TABLES:
        op.alter_column(table, "tenant_id", nullable=True)
        op.execute(text(f"UPDATE {table} SET tenant_id = NULL"))
```

Batching option (SQL only):
```sql
-- Repeat until 0 rows affected
UPDATE projects SET tenant_id = :tid
WHERE tenant_id IS NULL
AND ctid = ANY(
  ARRAY(SELECT ctid FROM projects WHERE tenant_id IS NULL LIMIT 10000)
);
```

## R5 — Composite uniques and indexes
Convert global uniques to tenant‑scoped ones. Example patterns:

```python
from alembic import op

revision = "r5_composite_uniques"
down_revision = "r4_backfill_tenant_id"

UNIQUES = [
    # (table, old_constraint_name, new_constraint_name, columns)
    ("projects", "uq_projects_name", "uq_projects_tenant_name", ["tenant_id", "name"]),
    ("tasks", "uq_tasks_uid", "uq_tasks_tenant_uid", ["tenant_id", "uid"]),
]

def upgrade():
    for table, old_uq, new_uq, cols in UNIQUES:
        # Drop old unique
        op.drop_constraint(old_uq, table, type_="unique")
        # Create new composite unique
        op.create_unique_constraint(new_uq, table, cols)


def downgrade():
    for table, old_uq, new_uq, cols in reversed(UNIQUES):
        op.drop_constraint(new_uq, table, type_="unique")
        op.create_unique_constraint(old_uq, table, cols[1:])  # original without tenant_id
```

Notes
- If original uniques were implicit (index‑backed), first introspect to get their names or recreate as needed.

## R6 — Enable RLS and policies
Enable RLS and add policies uniformly. Use explicit names for easy maintenance.

```python
from alembic import op

revision = "r6_enable_rls"
down_revision = "r5_composite_uniques"

TENANT_TABLES = ["tenants", "tenant_memberships", "invitations", "projects", "tasks"]  # extend

POLICY_TEMPLATE = """
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
-- Optional: FORCE ROW LEVEL SECURITY to prevent BYPASSRLS roles
-- ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS {table}_tenant_policy ON {table};
CREATE POLICY {table}_tenant_policy ON {table}
  USING (tenant_id = current_setting('app.tenant_id')::uuid AND (deleted_at IS NULL OR deleted_at IS NULL))
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
"""

def upgrade():
    for table in TENANT_TABLES:
        op.execute(POLICY_TEMPLATE.format(table=table))


def downgrade():
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_policy ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
```

Notes
- Do not apply RLS to truly global tables. If `tenants` itself should be tenant‑less for owners listing, skip it or create owner‑specific policy.
- If some tables lack `deleted_at`, simplify the `USING` clause accordingly.

## Smoke Test (psql)
```sql
-- As an app role with RLS enabled
SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000001';
SELECT COUNT(*) FROM projects;  -- should show only default tenant rows

SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000002';
SELECT COUNT(*) FROM projects;  -- should show 0 until seeded for tenant 2

-- Write path respects WITH CHECK
INSERT INTO projects (id, tenant_id, name) VALUES (gen_random_uuid(), '...0002', 'x');
-- Fails if app.tenant_id != '...0002'
```

## Downtime & Locking Considerations
- Adding columns NULL is metadata‑only; safe. Avoid `DEFAULT` on add.
- Setting NOT NULL requires a full table scan; do after backfill and during low traffic.
- Dropping/creating uniques takes locks; schedule in a short maintenance window.

## Observability Checklist
- Log `current_setting('app.tenant_id')` during integration tests to confirm session wiring.
- Track policy hits via `pg_stat_policy` (PG 16+) or verify via EXPLAIN and filters.

## Open Decisions
- Confirm users table name/type for FKs.
- Decide whether `tenants` is visible only to members (policy) or globally listable by admins.
- Determine cascade behavior on tenant deletion (prefer soft‑delete + background purge).

```text
End of outlines — ready for implementation as Alembic revisions.
```

