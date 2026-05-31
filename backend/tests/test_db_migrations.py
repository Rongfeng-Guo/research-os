from __future__ import annotations

from pathlib import Path

from sqlmodel import create_engine

from app import db


def test_bootstrap_legacy_database_for_alembic_stamps_initial_revision(monkeypatch, tmp_path: Path):
    legacy_db_path = tmp_path / "legacy.db"
    legacy_engine = create_engine(f"sqlite:///{legacy_db_path}", connect_args={"check_same_thread": False})
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE project (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, title TEXT NOT NULL, topic TEXT NOT NULL, description TEXT DEFAULT '')"
        )

    stamped: list[str] = []
    monkeypatch.setattr(db, "engine", legacy_engine)
    monkeypatch.setattr(db, "stamp_alembic_revision", lambda revision: stamped.append(revision))

    db.bootstrap_legacy_database_for_alembic()

    assert stamped == ["20260531_000001"]


def test_bootstrap_legacy_database_for_alembic_skips_empty_database(monkeypatch, tmp_path: Path):
    empty_db_path = tmp_path / "empty.db"
    empty_engine = create_engine(f"sqlite:///{empty_db_path}", connect_args={"check_same_thread": False})

    stamped: list[str] = []
    monkeypatch.setattr(db, "engine", empty_engine)
    monkeypatch.setattr(db, "stamp_alembic_revision", lambda revision: stamped.append(revision))

    db.bootstrap_legacy_database_for_alembic()

    assert stamped == []
