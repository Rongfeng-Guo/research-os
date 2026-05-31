import logging
from pathlib import Path

from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


def run_alembic_migrations(*, database_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[1]
    alembic_ini = backend_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def stamp_alembic_revision(*, database_url: str, revision: str) -> None:
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[1]
    alembic_ini = backend_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.stamp(config, revision)


def has_user_tables(*, engine) -> bool:
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
    return bool(table_names - {"alembic_version"})


def has_alembic_version_table(*, engine) -> bool:
    with engine.begin() as connection:
        inspector = inspect(connection)
        return "alembic_version" in set(inspector.get_table_names())


def get_alembic_revision(*, engine) -> str | None:
    if not has_alembic_version_table(engine=engine):
        return None
    with engine.begin() as connection:
        row = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
    return str(row[0]) if row else None


def bootstrap_legacy_database_for_alembic(*, engine, database_url: str) -> None:
    if not has_user_tables(engine=engine) or has_alembic_version_table(engine=engine):
        return
    stamp_alembic_revision(database_url=database_url, revision="20260531_000001")


def add_column_if_missing(*, engine, table_name: str, column_name: str, ddl: str) -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if column_name not in columns:
            connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def backfill_null(*, engine, table_name: str, column_name: str, replacement_sql: str) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            f"UPDATE {table_name} SET {column_name} = {replacement_sql} WHERE {column_name} IS NULL"
        )
