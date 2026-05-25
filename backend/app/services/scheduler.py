from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import ContextManager

from sqlmodel import Session, select

from ..db import engine
from ..models import Project, UpdateRun, User
from ..settings import settings
from ..time_utils import utc_now
from .digest_service import generate_workspace_digest, should_generate_scheduled_digest
from .project_health import ensure_refresh_schedule, project_is_due_for_refresh
from .refresh_workflow import run_project_refresh_job
from .update_runs import create_update_run


logger = logging.getLogger(__name__)

_scheduler_lock = threading.Lock()
_scheduler_started = False
_scheduler_stop_event: threading.Event | None = None
_scheduler_thread: threading.Thread | None = None


def _normalize_dt(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _project_has_running_refresh(session: Session, project_id: int) -> bool:
    running = session.exec(
        select(UpdateRun).where(
            UpdateRun.project_id == project_id,
            UpdateRun.run_type == "project_refresh",
            UpdateRun.status == "running",
        )
    ).first()
    return running is not None


def _default_session_factory() -> ContextManager[Session]:
    return Session(engine)


def run_due_refresh_cycle(
    *,
    now: datetime | None = None,
    session_factory: Callable[[], ContextManager[Session]] | None = None,
) -> int:
    cycle_now = _normalize_dt(now or utc_now())
    launched = 0
    with (session_factory or _default_session_factory)() as session:
        projects = session.exec(select(Project).where(Project.auto_refresh_enabled == True)).all()  # noqa: E712
        for project in projects:
            ensure_refresh_schedule(project, now=cycle_now)
            session.add(project)
        session.commit()

        for project in projects:
            if not project_is_due_for_refresh(project, now=cycle_now):
                continue
            if _project_has_running_refresh(session, project.id):
                continue

            logger.info("Starting scheduled refresh for project_id=%s title=%s", project.id, project.title)
            run = create_update_run(
                session,
                project_id=project.id,
                run_type="project_refresh",
                trigger_type="scheduled",
                provider="paper_discovery+extraction",
                summary="Scheduled refresh triggered by cadence",
                current_step="Queued",
                progress_message="Scheduler picked up a due refresh run.",
                total_steps=3,
            )
            session.refresh(project)
            run_project_refresh_job(session, project=project, run=run)
            project.updated_at = utc_now()
            session.add(project)
            session.commit()
            launched += 1
    return launched


def run_digest_cycle(
    *,
    now: datetime | None = None,
    session_factory: Callable[[], ContextManager[Session]] | None = None,
) -> int:
    cycle_now = _normalize_dt(now or utc_now())
    generated = 0
    with (session_factory or _default_session_factory)() as session:
        owners = session.exec(select(User)).all()
        for owner in owners:
            if not should_generate_scheduled_digest(
                session,
                owner_id=owner.id,
                now=cycle_now,
                days=settings.digest_window_days,
            ):
                continue
            logger.info("Generating scheduled digest for owner_id=%s", owner.id)
            generate_workspace_digest(
                session,
                owner_id=owner.id,
                days=settings.digest_window_days,
                persist=True,
                generated_from="scheduler",
            )
            generated += 1
    return generated


def _scheduler_loop(stop_event: threading.Event) -> None:
    logger.info("Background scheduler started with poll interval=%ss", settings.scheduler_poll_seconds)
    while not stop_event.wait(settings.scheduler_poll_seconds):
        try:
            launched = run_due_refresh_cycle()
            generated = run_digest_cycle()
            if launched or generated:
                logger.info(
                    "Background scheduler completed cycle with %s scheduled refreshes and %s digests",
                    launched,
                    generated,
                )
        except Exception:
            logger.exception("Background scheduler cycle failed")
    logger.info("Background scheduler stopped")


def start_scheduler() -> None:
    global _scheduler_started, _scheduler_stop_event, _scheduler_thread
    if not settings.scheduler_enabled:
        logger.info("Background scheduler disabled by configuration")
        return

    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_stop_event = threading.Event()
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            args=(_scheduler_stop_event,),
            name="research-os-scheduler",
            daemon=True,
        )
        _scheduler_thread.start()
        _scheduler_started = True


def stop_scheduler() -> None:
    global _scheduler_started, _scheduler_stop_event, _scheduler_thread
    with _scheduler_lock:
        if not _scheduler_started:
            return
        if _scheduler_stop_event is not None:
            _scheduler_stop_event.set()
        if _scheduler_thread is not None:
            _scheduler_thread.join(timeout=2)
        _scheduler_thread = None
        _scheduler_stop_event = None
        _scheduler_started = False
