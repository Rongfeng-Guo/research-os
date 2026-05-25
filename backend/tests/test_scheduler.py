from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, select

from app.db import get_session
from app.models import Project, UpdateRun
from app.models import WorkspaceDigest
from app.services.scheduler import run_digest_cycle, run_due_refresh_cycle
from app.time_utils import utc_now


def test_scheduler_runs_due_project_refresh(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Scheduled Project", "topic": "retrieval systems", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "daily", "digest_enabled": True},
        headers=auth_headers,
    )

    def fake_refresh_job(session, *, project, run, limit=8):
        run.papers_added = 2
        session.add(run)
        session.commit()
        project.last_refreshed_at = utc_now()
        session.add(project)
        session.commit()
        return [], [], []

    monkeypatch.setattr("app.services.scheduler.run_project_refresh_job", fake_refresh_job)

    override = client.app.dependency_overrides[get_session]

    def session_factory():
        return next(override())

    with next(override()) as session:
        project_obj = session.get(Project, project["id"])
        project_obj.last_refreshed_at = utc_now() - timedelta(days=2)
        project_obj.next_refresh_due_at = utc_now() - timedelta(minutes=5)
        session.add(project_obj)
        session.commit()

    launched = run_due_refresh_cycle(session_factory=session_factory)
    assert launched == 1

    with next(override()) as session:
        runs = session.exec(
            select(UpdateRun).where(UpdateRun.project_id == project["id"]).order_by(UpdateRun.created_at.desc())
        ).all()
        assert runs
        assert runs[0].trigger_type == "scheduled"
        assert runs[0].run_type == "project_refresh"


def test_scheduler_skips_manual_only_projects(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Manual Project", "topic": "manual topic", "description": ""},
        headers=auth_headers,
    ).json()

    called = {"value": 0}

    def fake_refresh_job(session, *, project, run, limit=8):
        called["value"] += 1
        return [], [], []

    monkeypatch.setattr("app.services.scheduler.run_project_refresh_job", fake_refresh_job)

    override = client.app.dependency_overrides[get_session]

    def session_factory():
        return next(override())

    with next(override()) as session:
        project_obj = session.get(Project, project["id"])
        project_obj.auto_refresh_enabled = False
        project_obj.refresh_cadence = "manual_only"
        project_obj.last_refreshed_at = utc_now() - timedelta(days=30)
        project_obj.next_refresh_due_at = utc_now() - timedelta(days=1)
        session.add(project_obj)
        session.commit()

    launched = run_due_refresh_cycle(session_factory=session_factory)
    assert launched == 0
    assert called["value"] == 0


def test_scheduler_skips_project_with_running_refresh(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Busy Project", "topic": "busy retrieval", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "daily", "digest_enabled": True},
        headers=auth_headers,
    )

    called = {"value": 0}

    def fake_refresh_job(session, *, project, run, limit=8):
        called["value"] += 1
        return [], [], []

    monkeypatch.setattr("app.services.scheduler.run_project_refresh_job", fake_refresh_job)

    override = client.app.dependency_overrides[get_session]

    def session_factory():
        return next(override())

    with next(override()) as session:
        project_obj = session.get(Project, project["id"])
        project_obj.last_refreshed_at = utc_now() - timedelta(days=3)
        project_obj.next_refresh_due_at = utc_now() - timedelta(minutes=5)
        session.add(project_obj)
        session.commit()

        running = UpdateRun(
            project_id=project["id"],
            status="running",
            run_type="project_refresh",
            trigger_type="manual",
            provider="paper_discovery+extraction",
            summary="Already running",
        )
        session.add(running)
        session.commit()

    launched = run_due_refresh_cycle(session_factory=session_factory)
    assert launched == 0
    assert called["value"] == 0


def test_scheduler_generates_digest_once_per_window(client, auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Digest Project", "topic": "digest topic", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "weekly", "digest_enabled": True},
        headers=auth_headers,
    )
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Digest source", "text": "This source adds weekly digest content.", "content_type": "text"},
        headers=auth_headers,
    )

    override = client.app.dependency_overrides[get_session]

    def session_factory():
        return next(override())

    first = run_digest_cycle(session_factory=session_factory)
    second = run_digest_cycle(session_factory=session_factory)

    assert first == 1
    assert second == 0

    with next(override()) as session:
        digests = session.exec(select(WorkspaceDigest)).all()
        assert len(digests) == 1
        project_obj = session.get(Project, project["id"])
        assert digests[0].owner_id == project_obj.owner_id
