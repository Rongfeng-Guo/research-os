from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import TOKEN_STORE, hash_password
from app.db import get_session
from app.main import app
from app.models import User
from app.services.scheduler import stop_scheduler


@pytest.fixture
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(email="test@example.com", password_hash=hash_password("password123"))
        session.add(user)
        second_user = User(email="second@example.com", password_hash=hash_password("password123"))
        session.add(second_user)
        session.commit()

    def override_get_session():
        with Session(engine) as session:
            yield session

    TOKEN_STORE.clear()
    original_startup = app.router.on_startup[:]
    original_shutdown = app.router.on_shutdown[:]
    app.router.on_startup = [handler for handler in app.router.on_startup if getattr(handler, "__name__", "") != "on_startup"]
    app.router.on_shutdown = [handler for handler in app.router.on_shutdown if getattr(handler, "__name__", "") != "on_shutdown"]
    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            SQLModel.metadata.create_all(engine)
            yield test_client
    finally:
        stop_scheduler()
        app.router.on_startup = original_startup
        app.router.on_shutdown = original_shutdown
        app.dependency_overrides.clear()
        TOKEN_STORE.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": "second@example.com", "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
