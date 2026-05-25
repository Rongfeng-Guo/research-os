import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..auth import get_current_user
from ..db import get_session
from ..models import EvidenceCard, Project, User
from ..schemas import EvidenceCardRead, EvidenceCardUpdate
from ..time_utils import utc_now

router = APIRouter(prefix="/evidence", tags=["evidence"])


def _card_to_read(card: EvidenceCard) -> EvidenceCardRead:
    return EvidenceCardRead(
        id=card.id,
        project_id=card.project_id,
        paper_id=card.paper_id,
        card_type=card.card_type,
        title=card.title,
        content=card.content,
        source_title=card.source_title or "",
        source_excerpt=card.source_excerpt or "",
        source_url=card.source_url or "",
        source_chunk_id=card.source_chunk_id or "",
        source_section=card.source_section or "",
        snippet_start=card.snippet_start,
        snippet_end=card.snippet_end,
        confidence_score=card.confidence_score or 0.0,
        provider_name=card.provider_name or "unknown",
        review_status=card.review_status or "suggested",
        is_pinned=bool(card.is_pinned),
        pinned_at=card.pinned_at,
        user_note=card.user_note or "",
        edited_at=card.edited_at,
        edited_by=card.edited_by or "",
        extracted_at=card.extracted_at or card.created_at,
        created_at=card.created_at,
    )


@router.get("/projects/{project_id}", response_model=List[EvidenceCardRead])
def list_project_evidence_cards(
    project_id: int,
    card_type: Optional[str] = Query(default=None),
    review_status: Optional[str] = Query(default=None),
    pinned: Optional[bool] = Query(default=None),
    source_title: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    statement = select(EvidenceCard).where(EvidenceCard.project_id == project_id)
    if card_type:
        statement = statement.where(EvidenceCard.card_type == card_type)
    if review_status:
        statement = statement.where(EvidenceCard.review_status == review_status)
    if pinned is not None:
        statement = statement.where(EvidenceCard.is_pinned == pinned)
    if source_title:
        statement = statement.where(EvidenceCard.source_title == source_title)

    cards = session.exec(statement).all()
    return [_card_to_read(card) for card in cards]


@router.patch("/{card_id}", response_model=EvidenceCardRead)
def update_evidence_card(
    card_id: int,
    payload: EvidenceCardUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    card = session.get(EvidenceCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Evidence card not found")

    project = session.get(Project, card.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.review_status and payload.review_status not in {"suggested", "accepted", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid review status")
    if payload.confidence_score is not None and not 0 <= payload.confidence_score <= 1:
        raise HTTPException(status_code=400, detail="Confidence score must be between 0 and 1")
    if payload.card_type and payload.card_type not in {"claim", "method", "dataset", "limitation", "open_question"}:
        raise HTTPException(status_code=400, detail="Invalid evidence type")

    snapshot = {
        "card_type": card.card_type,
        "title": card.title,
        "content": card.content,
        "source_title": card.source_title,
        "source_excerpt": card.source_excerpt,
        "source_section": card.source_section,
        "confidence_score": card.confidence_score,
        "review_status": card.review_status,
        "is_pinned": card.is_pinned,
        "user_note": card.user_note,
    }

    if payload.card_type is not None:
        card.card_type = payload.card_type
    if payload.title is not None:
        card.title = payload.title
    if payload.content is not None:
        card.content = payload.content
    if payload.source_title is not None:
        card.source_title = payload.source_title
    if payload.source_excerpt is not None:
        card.source_excerpt = payload.source_excerpt
    if payload.source_section is not None:
        card.source_section = payload.source_section
    if payload.confidence_score is not None:
        card.confidence_score = payload.confidence_score
    if payload.review_status is not None:
        card.review_status = payload.review_status
    if payload.is_pinned is not None:
        card.is_pinned = payload.is_pinned
        card.pinned_at = utc_now() if payload.is_pinned else None
    if payload.user_note is not None:
        card.user_note = payload.user_note

    card.edit_snapshot_json = json.dumps(snapshot)
    card.edited_at = utc_now()
    card.edited_by = "user"
    project.updated_at = utc_now()
    session.add(card)
    session.add(project)
    session.commit()
    session.refresh(card)
    return _card_to_read(card)


@router.post("/{card_id}/pin", response_model=EvidenceCardRead)
def pin_evidence_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return update_evidence_card(
        card_id=card_id,
        payload=EvidenceCardUpdate(is_pinned=True),
        current_user=current_user,
        session=session,
    )


@router.post("/{card_id}/unpin", response_model=EvidenceCardRead)
def unpin_evidence_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return update_evidence_card(
        card_id=card_id,
        payload=EvidenceCardUpdate(is_pinned=False),
        current_user=current_user,
        session=session,
    )
