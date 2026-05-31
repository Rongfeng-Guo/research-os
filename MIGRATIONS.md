# Database Migrations

This project now treats Alembic as the normal migration path.

## Normal startup modes

- `DATABASE_MIGRATION_MODE=hybrid`
  Bootstraps pre-Alembic legacy databases by stamping the initial revision, then upgrades through the Alembic chain.
- `DATABASE_MIGRATION_MODE=alembic`
  Assumes the database is already Alembic-managed and only runs Alembic.

## Normal commands

```powershell
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

Or from the repo root:

```powershell
make backend-migrate
make backend-migration-create MESSAGE="describe change"
```

## Health visibility

The backend now reports migration state through:

- `GET /health`
- `GET /health/ready`

Fields:

- `database_migration_mode`
- `alembic_revision`

This makes it easier to confirm which revision a running instance is using.

## Legacy fallback

The application no longer supports `DATABASE_MIGRATION_MODE=lightweight` during startup.

If an older database still requires the deprecated runtime column patching path, use the standalone operator script described in [LEGACY_MIGRATION.md](LEGACY_MIGRATION.md).

## Recommended operator workflow

1. Keep normal environments on `hybrid` or `alembic`.
2. Apply new revisions with `alembic upgrade head`.
3. Check `/health` or `/health/ready` to confirm the expected `alembic_revision`.
4. Use the legacy script only for exceptional recovery of very old local databases.
