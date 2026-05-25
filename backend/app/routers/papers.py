import json
import logging
from typing import List

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from ..auth import get_current_user
from ..db import engine, get_session
from ..models import EvidenceCard, Project, ProjectPaper, SearchRun, SourcePaper, UpdateRun, User
from ..schemas import AddPaperRequest, EvidenceCardRead, LinkedProjectRef, PaperCandidate, PaperDetailRequest, PaperLibraryItem, PaperReadRequest, PaperSearchRequest, UpdateRunRead, UploadTextRequest
from ..services.paper_reader import read_paper_by_external_id
from ..services.extraction_service import extract_structured_evidence
from ..services.ingestion import create_source_paper_from_text, ingest_uploaded_file
from ..services.paper_search import get_paper_discovery_provider, search_papers as run_paper_search
from ..services.update_runs import create_update_run, finish_update_run, update_update_run
from ..settings import settings
from ..time_utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])


def _snippet_offsets(full_text: str, snippet: str, chunk_start: int) -> tuple[int | None, int | None]:
    compact_snippet = (snippet or "").strip()
    if not compact_snippet:
        return None, None
    local_offset = full_text.find(compact_snippet)
    if local_offset >= 0:
        return local_offset, local_offset + len(compact_snippet)
    return chunk_start, chunk_start + min(len(compact_snippet), 280)


def _parse_source_metadata(raw: str) -> dict:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def _paper_candidate_payload(paper: SourcePaper) -> dict:
    return {
        "external_id": paper.external_id,
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": paper.authors,
        "year": paper.year,
        "source": paper.source,
        "url": paper.url,
        "content_text": paper.content_text,
        "content_type": paper.content_type,
        "source_type": paper.source_type,
        "origin": paper.origin,
        "ingestion_status": paper.ingestion_status,
        "pdf_status": paper.pdf_status,
        "extraction_status": paper.extraction_status,
        "extraction_error": paper.extraction_error,
        "source_metadata": _parse_source_metadata(paper.source_metadata),
    }


def _run_to_read(run: UpdateRun) -> UpdateRunRead:
    return UpdateRunRead.model_validate(run)


def _run_extraction_workflow(session: Session, *, project_id: int, run: UpdateRun) -> list[EvidenceCard]:
    joins = session.exec(select(ProjectPaper).where(ProjectPaper.project_id == project_id)).all()
    pending_papers: list[SourcePaper] = []
    for join in joins:
        paper = session.get(SourcePaper, join.paper_id)
        if not paper:
            continue
        already_exists = session.exec(
            select(EvidenceCard).where(EvidenceCard.project_id == project_id, EvidenceCard.paper_id == paper.id)
        ).first()
        if already_exists:
            continue
        pending_papers.append(paper)

    update_update_run(
        session,
        run,
        current_step="Scanning project sources",
        progress_message=f"Found {len(pending_papers)} sources that still need extraction.",
        total_steps=max(1, len(pending_papers)),
        completed_steps=0,
    )

    created_cards: list[EvidenceCard] = []
    has_partial = False
    total = len(pending_papers)
    for index, paper in enumerate(pending_papers, start=1):
        update_update_run(
            session,
            run,
            current_step=f"Extracting {paper.title[:80]}",
            progress_message=f"Processing source {index}/{total}: {paper.title}",
            completed_steps=index - 1,
        )
        workflow = extract_structured_evidence(
            title=paper.title,
            text=paper.content_text or paper.abstract,
            source_url=paper.url,
        )
        if workflow.status == "failed" or not workflow.result:
            paper.extraction_status = "failed"
            paper.extraction_error = workflow.error_message
            session.add(paper)
            session.commit()
            has_partial = True
            update_update_run(
                session,
                run,
                progress_message=f"Source {index}/{total} failed. Continuing with remaining sources.",
                completed_steps=index,
            )
            continue

        paper.extraction_status = workflow.status
        paper.extraction_error = workflow.error_message or " | ".join(workflow.warning_messages)
        session.add(paper)
        if workflow.status == "partial":
            has_partial = True
        for card_type, item in workflow.result.iter_cards():
            chunk = next(
                (
                    known_chunk
                    for known_chunk in workflow.chunks
                    if known_chunk.section_name == item.section_name and item.snippet and item.snippet in known_chunk.text
                ),
                workflow.chunks[0] if workflow.chunks else None,
            )
            snippet_start, snippet_end = _snippet_offsets(
                paper.content_text or paper.abstract or "",
                item.snippet,
                chunk.start_char if chunk else 0,
            )
            obj = EvidenceCard(
                project_id=project_id,
                paper_id=paper.id,
                card_type=card_type,
                title=f"{card_type.replace('_', ' ').title()} from {paper.title}",
                content=item.content,
                source_title=paper.title,
                source_excerpt=(item.snippet or (chunk.text[:280] if chunk else ""))[:280].strip(),
                source_url=paper.url,
                source_chunk_id=chunk.chunk_id if chunk else "",
                source_section=item.section_name or (chunk.section_name if chunk else ""),
                snippet_start=snippet_start,
                snippet_end=snippet_end,
                confidence_score=item.confidence_score,
                provider_name=workflow.provider,
                review_status="suggested",
                extraction_run_id=run.id,
                extracted_at=utc_now(),
            )
            session.add(obj)
            session.flush()
            created_cards.append(obj)
        session.commit()
        update_update_run(
            session,
            run,
            progress_message=f"Processed {index}/{total} sources and created {len(created_cards)} evidence cards.",
            evidence_created=len(created_cards),
            completed_steps=index,
        )

    project = session.get(Project, project_id)
    if project:
        project.updated_at = utc_now()
        session.add(project)
        session.commit()

    run_status = "partial" if has_partial else "completed"
    finish_update_run(session, run, status=run_status, summary=f"Created {len(created_cards)} evidence cards")
    for card in created_cards:
        session.refresh(card)
    return created_cards


def _run_extraction_task(project_id: int, run_id: int) -> None:
    with Session(engine) as session:
        run = session.get(UpdateRun, run_id)
        project = session.get(Project, project_id)
        if not run or not project:
            return
        try:
            _run_extraction_workflow(session, project_id=project_id, run=run)
        except Exception as exc:
            finish_update_run(session, run, status="failed", summary="Extraction failed", error_message=str(exc))


@router.post("/search", response_model=List[PaperCandidate])
def search_papers_route(
    payload: PaperSearchRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _ = current_user
    provider = get_paper_discovery_provider()
    try:
        results = run_paper_search(payload.query, limit=payload.limit)
        session.add(
            SearchRun(
                project_id=0,
                query=payload.query,
                provider=provider.provider_name,
                status="completed",
            )
        )
        session.commit()
    except Exception as exc:
        logger.exception("Search failed for query=%s", payload.query)
        session.add(
            SearchRun(
                project_id=0,
                query=payload.query,
                provider=provider.provider_name,
                status="failed",
                error_message=str(exc),
            )
        )
        session.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [PaperCandidate(**row) for row in results]


@router.post("/detail", response_model=PaperCandidate)
def get_paper_detail_route(
    payload: PaperDetailRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _ = current_user
    paper = session.exec(select(SourcePaper).where(SourcePaper.external_id == payload.external_id)).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return PaperCandidate(**_paper_candidate_payload(paper))


@router.post("/read", response_model=PaperCandidate)
def read_paper_route(
    payload: PaperReadRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _ = current_user
    try:
        paper = read_paper_by_external_id(session=session, external_id=payload.external_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        detail = f"Remote paper read failed: {exc}"
        if status_code == 404:
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Remote paper read failed: {exc}") from exc
    except Exception as exc:
        logger.exception("Paper read failed for external_id=%s", payload.external_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return PaperCandidate(**paper.to_dict())


@router.get("/library", response_model=List[PaperLibraryItem])
def list_library_papers(
    query: str = "",
    source: str = "",
    origin: str = "",
    limit: int = 24,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    projects = session.exec(select(Project).where(Project.owner_id == current_user.id)).all()
    if not projects:
        return []

    project_ids = [project.id for project in projects if project.id is not None]
    if not project_ids:
        return []

    links = session.exec(select(ProjectPaper).where(ProjectPaper.project_id.in_(project_ids))).all()
    if not links:
        return []

    project_by_id = {project.id: project for project in projects if project.id is not None}
    paper_to_project_ids: dict[int, set[int]] = {}
    for link in links:
        if link.paper_id is None or link.project_id is None:
            continue
        paper_to_project_ids.setdefault(link.paper_id, set()).add(link.project_id)

    if not paper_to_project_ids:
        return []

    paper_ids = list(paper_to_project_ids.keys())
    papers = session.exec(select(SourcePaper).where(SourcePaper.id.in_(paper_ids))).all()

    query_filter = query.strip().lower()
    source_filter = source.strip().lower()
    origin_filter = origin.strip().lower()
    max_items = max(1, min(limit, 200))
    items: list[PaperLibraryItem] = []

    for paper in sorted(
        papers,
        key=lambda item: (
            item.ingested_at,
            item.source_updated_at,
            item.created_at,
        ),
        reverse=True,
    ):
        if source_filter and (paper.source or "").lower() != source_filter:
            continue
        if origin_filter and (paper.origin or "").lower() != origin_filter:
            continue
        if query_filter:
            searchable_text = " ".join(
                [
                    paper.external_id or "",
                    paper.title or "",
                    paper.abstract or "",
                    paper.authors or "",
                    paper.source or "",
                    paper.origin or "",
                ]
            ).lower()
            if query_filter not in searchable_text:
                continue

        linked_projects = [
            LinkedProjectRef(id=project.id, title=project.title)
            for project_id in sorted(paper_to_project_ids.get(paper.id or 0, set()))
            for project in [project_by_id.get(project_id)]
            if project is not None and project.id is not None
        ]

        items.append(
            PaperLibraryItem(
                id=paper.id,
                project_count=len(linked_projects),
                linked_projects=linked_projects,
                ingested_at=paper.ingested_at,
                source_updated_at=paper.source_updated_at,
                created_at=paper.created_at,
                **_paper_candidate_payload(paper),
            )
        )
        if len(items) >= max_items:
            break

    return items


@router.post("/projects/{project_id}/add", response_model=PaperCandidate)
def add_paper_to_project(
    project_id: int,
    payload: AddPaperRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = session.exec(select(SourcePaper).where(SourcePaper.external_id == payload.external_id)).first()
    if not existing:
        body = payload.model_dump()
        body["source_metadata"] = json.dumps(body.get("source_metadata", {}))
        existing = SourcePaper(**body)
        session.add(existing)
        session.commit()
        session.refresh(existing)

    link = session.exec(
        select(ProjectPaper).where(ProjectPaper.project_id == project_id, ProjectPaper.paper_id == existing.id)
    ).first()
    if not link:
        session.add(ProjectPaper(project_id=project_id, paper_id=existing.id))

    session.add(SearchRun(project_id=project_id, query=payload.title, provider=payload.source, status="completed"))
    project.updated_at = utc_now()
    session.add(project)
    session.commit()

    return PaperCandidate(**payload.model_dump())


@router.post("/projects/{project_id}/upload-text")
def upload_text_to_project(
    project_id: int,
    payload: UploadTextRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    paper = SourcePaper(
        **create_source_paper_from_text(
            title=payload.title,
            text=payload.text,
            origin="upload_text",
            source_type=payload.content_type,
            external_id=f"upload-{project_id}-{int(utc_now().timestamp())}",
            authors=payload.authors or "Uploaded by user",
            year=payload.year,
            url=payload.url,
            metadata={"provider": "upload", "mode": "text"},
        ).model_dump()
    )
    session.add(paper)
    session.commit()
    session.refresh(paper)
    session.add(ProjectPaper(project_id=project_id, paper_id=paper.id))
    # TODO: move ingestion and extraction into background jobs once the MVP needs queueing.
    project.updated_at = utc_now()
    session.add(project)
    session.commit()
    return {"message": "Text uploaded", "paper_id": paper.id, "title": paper.title}


@router.post("/projects/{project_id}/upload-file")
async def upload_file_to_project(
    project_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    paper = await ingest_uploaded_file(project_id=project_id, file=file)
    session.add(paper)
    session.commit()
    session.refresh(paper)
    session.add(ProjectPaper(project_id=project_id, paper_id=paper.id))
    project.updated_at = utc_now()
    session.add(project)
    session.commit()
    return {"message": "File uploaded", "paper_id": paper.id, "title": paper.title, "source_type": paper.source_type}


@router.post("/projects/{project_id}/extract", response_model=List[EvidenceCardRead])
def run_extraction(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    run = create_update_run(
        session,
        project_id=project_id,
        run_type="extraction",
        trigger_type="manual",
        provider=settings.extraction_provider,
        summary="Evidence extraction requested",
        current_step="Queued",
        progress_message="Preparing extraction workflow...",
    )
    created_cards = _run_extraction_workflow(session, project_id=project_id, run=run)
    return [EvidenceCardRead.model_validate(card) for card in created_cards]


@router.post("/projects/{project_id}/extract/start", response_model=UpdateRunRead)
def start_extraction(
    project_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    running = session.exec(
        select(UpdateRun).where(
            UpdateRun.project_id == project_id,
            UpdateRun.run_type == "extraction",
            UpdateRun.status == "running",
        )
    ).first()
    if running:
        return _run_to_read(running)

    run = create_update_run(
        session,
        project_id=project_id,
        run_type="extraction",
        trigger_type="manual",
        provider=settings.extraction_provider,
        summary="Evidence extraction requested",
        current_step="Queued",
        progress_message="Extraction job has been scheduled.",
    )
    background_tasks.add_task(_run_extraction_task, project_id, run.id)
    return _run_to_read(run)
