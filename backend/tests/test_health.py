from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app import main


def test_health_includes_migration_metadata(client, monkeypatch):
    monkeypatch.setattr(main, "get_alembic_revision", lambda **kwargs: "20260531_000002")

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database_migration_mode"] in {"hybrid", "alembic"}
    assert payload["alembic_revision"] == "20260531_000002"


def test_ready_health_includes_revision_and_database_ok(client, monkeypatch, tmp_path):
    db_path = tmp_path / "ready-health.db"
    ready_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(ready_engine)
    monkeypatch.setattr(main, "engine", ready_engine)
    monkeypatch.setattr(main, "get_alembic_revision", lambda **kwargs: "20260531_000002")

    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] == "ok"
    assert payload["alembic_revision"] == "20260531_000002"
