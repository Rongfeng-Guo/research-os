from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sqlmodel import create_engine

from app import db
from app import migration_bootstrap
from scripts import legacy_lightweight_migrate
from app.settings import Settings


def test_bootstrap_legacy_database_for_alembic_stamps_initial_revision(monkeypatch, tmp_path: Path):
    legacy_db_path = tmp_path / "legacy.db"
    legacy_engine = create_engine(f"sqlite:///{legacy_db_path}", connect_args={"check_same_thread": False})
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE project (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, title TEXT NOT NULL, topic TEXT NOT NULL, description TEXT DEFAULT '')"
        )

    stamped: list[str] = []
    monkeypatch.setattr(migration_bootstrap, "stamp_alembic_revision", lambda **kwargs: stamped.append(kwargs["revision"]))

    migration_bootstrap.bootstrap_legacy_database_for_alembic(engine=legacy_engine, database_url="sqlite:///legacy.db")

    assert stamped == ["20260531_000001"]


def test_bootstrap_legacy_database_for_alembic_skips_empty_database(monkeypatch, tmp_path: Path):
    empty_db_path = tmp_path / "empty.db"
    empty_engine = create_engine(f"sqlite:///{empty_db_path}", connect_args={"check_same_thread": False})

    stamped: list[str] = []
    monkeypatch.setattr(migration_bootstrap, "stamp_alembic_revision", lambda **kwargs: stamped.append(kwargs["revision"]))

    migration_bootstrap.bootstrap_legacy_database_for_alembic(engine=empty_engine, database_url="sqlite:///empty.db")

    assert stamped == []


def test_legacy_script_requires_confirm(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["legacy_lightweight_migrate.py"])

    code = legacy_lightweight_migrate.main()

    captured = capsys.readouterr()
    assert code == 2
    assert "Refusing to run legacy lightweight migrations without --confirm" in captured.err


def test_legacy_script_emits_warning_and_runs(monkeypatch, caplog):
    calls: list[str] = []
    monkeypatch.setattr("sys.argv", ["legacy_lightweight_migrate.py", "--confirm"])
    monkeypatch.setattr(legacy_lightweight_migrate, "add_column_if_missing", lambda **kwargs: calls.append("add"))
    monkeypatch.setattr(legacy_lightweight_migrate, "backfill_null", lambda **kwargs: calls.append("backfill"))
    monkeypatch.setattr(legacy_lightweight_migrate.SQLModel.metadata, "create_all", lambda engine: calls.append("create_all"))

    import logging
    import warnings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with caplog.at_level(logging.WARNING):
            code = legacy_lightweight_migrate.main()

    assert code == 0
    assert "deprecated legacy lightweight migration script" in caplog.text.lower()
    assert any(item.category is DeprecationWarning for item in caught)
    assert "create_all" in calls
    assert "add" in calls
    assert "backfill" in calls


def test_legacy_script_dry_run_skips_database_writes(monkeypatch, capsys):
    calls: list[str] = []
    monkeypatch.setattr("sys.argv", ["legacy_lightweight_migrate.py", "--confirm", "--dry-run"])
    monkeypatch.setattr(legacy_lightweight_migrate, "add_column_if_missing", lambda **kwargs: calls.append("add"))
    monkeypatch.setattr(legacy_lightweight_migrate, "backfill_null", lambda **kwargs: calls.append("backfill"))
    monkeypatch.setattr(legacy_lightweight_migrate.SQLModel.metadata, "create_all", lambda engine: calls.append("create_all"))

    code = legacy_lightweight_migrate.main()

    captured = capsys.readouterr()
    assert code == 0
    assert "Dry run complete." in captured.out
    assert calls == []


def test_create_db_and_tables_uses_lightweight_path(monkeypatch):
    import pytest

    settings = Settings(database_migration_mode="lightweight")

    with pytest.raises(ValueError, match="DATABASE_MIGRATION_MODE must be one of: alembic, hybrid"):
        settings.validate()


def test_create_db_and_tables_uses_hybrid_path(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(db, "settings", SimpleNamespace(database_migration_mode="hybrid", database_url="sqlite:///hybrid.db"))
    monkeypatch.setattr(db, "bootstrap_legacy_database_for_alembic", lambda **kwargs: calls.append("bootstrap"))
    monkeypatch.setattr(db, "run_alembic_migrations", lambda **kwargs: calls.append("alembic"))

    db.create_db_and_tables()

    assert calls == ["bootstrap", "alembic"]


def test_create_db_and_tables_uses_alembic_only_path(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(db, "settings", SimpleNamespace(database_migration_mode="alembic", database_url="sqlite:///alembic.db"))
    monkeypatch.setattr(db, "bootstrap_legacy_database_for_alembic", lambda **kwargs: calls.append("bootstrap"))
    monkeypatch.setattr(db, "run_alembic_migrations", lambda **kwargs: calls.append("alembic"))

    db.create_db_and_tables()

    assert calls == ["bootstrap", "alembic"]


def test_settings_reject_lightweight_mode():
    settings = Settings(database_migration_mode="lightweight")

    import pytest

    with pytest.raises(ValueError, match="DATABASE_MIGRATION_MODE must be one of: alembic, hybrid"):
        settings.validate()
