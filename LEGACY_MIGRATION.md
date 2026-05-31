# Legacy Migration Fallback

`DATABASE_MIGRATION_MODE=lightweight` is deprecated.

Use it only as a temporary emergency fallback when an older local database cannot yet enter the Alembic-managed path.

## Normal modes

- `hybrid`: default, stamps pre-Alembic legacy databases into the Alembic chain and then upgrades to head
- `alembic`: runs Alembic only

## Deprecated fallback

`lightweight` still exists only for recovery scenarios and now requires:

```powershell
DATABASE_MIGRATION_MODE=lightweight
LIGHTWEIGHT_MIGRATION_CONFIRM=true
```

Without `LIGHTWEIGHT_MIGRATION_CONFIRM=true`, startup validation fails.

When this mode is used, the backend also emits:

- a `DeprecationWarning`
- a runtime warning log entry

## Exit strategy

After recovering the database:

1. Switch back to `DATABASE_MIGRATION_MODE=hybrid`
2. Run `alembic upgrade head`
3. Verify the database reaches the current Alembic revision chain
4. Remove `LIGHTWEIGHT_MIGRATION_CONFIRM`

The project direction is to remove the lightweight runtime patching path entirely after legacy users have moved onto Alembic-managed revisions.
