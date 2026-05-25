from __future__ import annotations

import logging
import json

from sqlmodel import Session, select

from ..models import EvidenceCard, NoteUpdateSuggestion, Project, ProjectPaper, SourcePaper, TopicNote, UpdateRun
from ..services.extraction_service import extract_structured_evidence
from ..services.paper_search import search_papers
from ..services.project_health import ensure_refresh_schedule
from ..services.update_runs import finish_update_run
from ..services.update_runs import update_update_run
from ..services.update_suggestions import create_update_suggestions
from ..time_utils import utc_now


logger = logging.getLogger(__name__)


def run_project_refresh(session: Session, *, project: Project, update_run: UpdateRun, limit: int = 8) -> tuple[list[SourcePaper], list[EvidenceCard], list[NoteUpdateSuggestion]]:
    update_update_run(
        session,
        update_run,
        current_step="Searching for new papers",
        progress_message=f"Searching for papers related to {project.topic}...",
        total_steps=3,
        completed_steps=0,
        refresh=False,
    )
    search_results = search_papers(project.topic, limit=limit)
    candidate_results = [row for row in search_results]
    update_update_run(
        session,
        update_run,
        current_step="Processing new papers",
        progress_message=f"Found {len(candidate_results)} candidates. Ingesting new papers...",
        papers_found=len(candidate_results),
        total_steps=max(3, len(candidate_results) + 2),
        completed_steps=1,
    )

    existing_external_ids = {
        paper.external_id
        for join in session.exec(select(ProjectPaper).where(ProjectPaper.project_id == project.id)).all()
        for paper in [session.get(SourcePaper, join.paper_id)]
        if paper
    }

    new_papers: list[SourcePaper] = []
    new_cards: list[EvidenceCard] = []
    processed_count = 0
    for row in candidate_results:
        processed_count += 1
        if row["external_id"] in existing_external_ids:
            update_update_run(
                session,
                update_run,
                progress_message=f"Checked {processed_count}/{len(candidate_results)} candidates...",
                completed_steps=min(update_run.total_steps - 1, 1 + processed_count),
            )
            continue
        body = dict(row)
        body["source_metadata"] = json.dumps(body.get("source_metadata", {}))
        paper = SourcePaper(**body)
        session.add(paper)
        session.commit()
        session.refresh(paper)
        session.add(ProjectPaper(project_id=project.id, paper_id=paper.id))
        session.commit()
        new_papers.append(paper)

        workflow = extract_structured_evidence(title=paper.title, text=paper.content_text or paper.abstract, source_url=paper.url)
        paper.extraction_status = workflow.status
        paper.extraction_error = workflow.error_message
        session.add(paper)
        session.commit()
        if not workflow.result:
            continue

        for card_type, item in workflow.result.iter_cards():
            card = EvidenceCard(
                project_id=project.id,
                paper_id=paper.id,
                card_type=card_type,
                title=f"{card_type.replace('_', ' ').title()} from {paper.title}",
                content=item.content,
                source_title=paper.title,
                source_excerpt=item.snippet[:280],
                source_url=paper.url,
                source_chunk_id="refresh",
                source_section=item.section_name,
                confidence_score=item.confidence_score,
                provider_name=workflow.provider,
                review_status="suggested",
                extraction_run_id=update_run.id,
                extracted_at=utc_now(),
            )
            session.add(card)
            session.flush()
            new_cards.append(card)
        update_update_run(
            session,
            update_run,
            progress_message=f"Processed {processed_count}/{len(candidate_results)} candidates and created {len(new_cards)} evidence cards.",
            completed_steps=min(update_run.total_steps - 1, 1 + processed_count),
        )

    update_update_run(
        session,
        update_run,
        current_step="Generating note update suggestions",
        progress_message=f"Creating note suggestions from {len(new_cards)} new evidence cards...",
        papers_added=len(new_papers),
        evidence_created=len(new_cards),
        completed_steps=max(update_run.total_steps - 1, 0),
    )

    note = session.exec(select(TopicNote).where(TopicNote.project_id == project.id)).first()
    suggestions = create_update_suggestions(
        session,
        project=project,
        note=note,
        update_run_id=update_run.id,
        new_evidence_cards=new_cards,
    )
    update_update_run(
        session,
        update_run,
        progress_message=f"Generated {len(suggestions)} suggestions across {len({suggestion.target_section for suggestion in suggestions})} sections.",
        affected_sections_count=len({suggestion.target_section for suggestion in suggestions}),
    )
    project.last_refreshed_at = utc_now()
    ensure_refresh_schedule(project)
    session.add(project)
    session.commit()
    return new_papers, new_cards, suggestions


def run_project_refresh_job(session: Session, *, project: Project, run: UpdateRun, limit: int = 8) -> tuple[list[SourcePaper], list[EvidenceCard], list[NoteUpdateSuggestion]]:
    try:
        update_update_run(
            session,
            run,
            current_step="Searching for new papers",
            progress_message="Contacting paper discovery providers...",
            total_steps=3,
            completed_steps=0,
        )
        new_papers, new_cards, suggestions = run_project_refresh(session, project=project, update_run=run, limit=limit)
        summary = f"Refresh finished with {len(new_papers)} new papers and {len(suggestions)} suggestions"
        finish_update_run(session, run, status="completed", summary=summary)
        return new_papers, new_cards, suggestions
    except Exception as exc:
        logger.exception("Project refresh job failed project_id=%s run_id=%s", project.id, run.id)
        finish_update_run(session, run, status="failed", summary="Refresh failed", error_message=str(exc))
        raise
