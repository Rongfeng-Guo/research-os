from __future__ import annotations

from sqlmodel import Session

from ..models import UpdateRun
from ..time_utils import utc_now


def create_update_run(
    session: Session,
    *,
    project_id: int,
    run_type: str,
    trigger_type: str,
    provider: str = "",
    summary: str = "",
    current_step: str = "",
    progress_message: str = "",
    total_steps: int = 0,
    completed_steps: int = 0,
) -> UpdateRun:
    run = UpdateRun(
        project_id=project_id,
        run_type=run_type,
        trigger_type=trigger_type,
        provider=provider,
        status="running",
        summary=summary,
        current_step=current_step,
        progress_message=progress_message,
        total_steps=total_steps,
        completed_steps=completed_steps,
        started_at=utc_now(),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def update_update_run(
    session: Session,
    run: UpdateRun,
    *,
    status: str | None = None,
    summary: str | None = None,
    error_message: str | None = None,
    current_step: str | None = None,
    progress_message: str | None = None,
    total_steps: int | None = None,
    completed_steps: int | None = None,
    papers_found: int | None = None,
    papers_added: int | None = None,
    evidence_created: int | None = None,
    affected_sections_count: int | None = None,
    refresh: bool = True,
) -> UpdateRun:
    if status is not None:
        run.status = status
    if summary is not None:
        run.summary = summary
    if error_message is not None:
        run.error_message = error_message
    if current_step is not None:
        run.current_step = current_step
    if progress_message is not None:
        run.progress_message = progress_message
    if total_steps is not None:
        run.total_steps = total_steps
    if completed_steps is not None:
        run.completed_steps = completed_steps
    if papers_found is not None:
        run.papers_found = papers_found
    if papers_added is not None:
        run.papers_added = papers_added
    if evidence_created is not None:
        run.evidence_created = evidence_created
    if affected_sections_count is not None:
        run.affected_sections_count = affected_sections_count
    session.add(run)
    session.commit()
    if refresh:
        session.refresh(run)
    return run


def finish_update_run(session: Session, run: UpdateRun, *, status: str, summary: str = "", error_message: str = "") -> UpdateRun:
    run.status = status
    run.summary = summary
    run.error_message = error_message
    run.current_step = ""
    run.progress_message = ""
    if run.total_steps and run.completed_steps < run.total_steps and status in {"completed", "partial"}:
        run.completed_steps = run.total_steps
    run.finished_at = utc_now()
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
