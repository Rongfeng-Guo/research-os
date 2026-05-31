from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sqlmodel import create_engine

from app import db
from app import migration_bootstrap
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


def test_lightweight_migrations_emit_deprecation_warning(tmp_path: Path):
    db_path = tmp_path / "lightweight.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    import warnings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        migration_bootstrap.run_lightweight_migrations(engine=engine)

    assert any(item.category is DeprecationWarning for item in caught)


def test_lightweight_migrations_log_runtime_warning(tmp_path: Path, caplog):
    db_path = tmp_path / "lightweight-log.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    import logging

    with caplog.at_level(logging.WARNING):
        migration_bootstrap.run_lightweight_migrations(engine=engine)

    assert "DATABASE_MIGRATION_MODE=lightweight is deprecated" in caplog.text


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
