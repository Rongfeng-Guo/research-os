# Legacy Migration Fallback

The application no longer accepts `DATABASE_MIGRATION_MODE=lightweight` during normal startup.

The old lightweight runtime patching path now exists only as a standalone emergency script for older databases that cannot yet enter the Alembic-managed path.

## Normal modes

- `hybrid`: default, stamps pre-Alembic legacy databases into the Alembic chain and then upgrades to head
- `alembic`: runs Alembic only

## Deprecated fallback script

Use the standalone backend script only for recovery scenarios:

```powershell
cd backend
python scripts/legacy_lightweight_migrate.py --confirm
```

When this mode is used, the backend also emits:

- a `DeprecationWarning`
- a runtime warning log entry

## Exit strategy

After recovering the database:

1. Switch back to `DATABASE_MIGRATION_MODE=hybrid`
2. Run `alembic upgrade head`
3. Verify the database reaches the current Alembic revision chain
4. Stop using the legacy script entirely

The project direction is to remove the lightweight runtime patching path entirely after legacy users have moved onto Alembic-managed revisions.
