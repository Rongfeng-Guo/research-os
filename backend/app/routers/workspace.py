from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..auth import get_current_user
from ..db import get_session
from ..models import WorkspaceDigest, User
from ..schemas import DashboardSummary, DigestDeliveryRead, DigestDeliveryRequest, WorkspaceDigestRead
from ..services.dashboard_service import build_workspace_summary
from ..services.digest_delivery import deliver_digest
from ..services.digest_service import digest_to_read, generate_workspace_digest

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/summary", response_model=DashboardSummary)
def get_workspace_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return DashboardSummary(**build_workspace_summary(session, current_user))


@router.post("/digests/generate", response_model=WorkspaceDigestRead)
def generate_digest(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    digest = generate_workspace_digest(session, current_user=current_user, days=days, persist=True)
    return WorkspaceDigestRead(**digest_to_read(digest))


@router.get("/digests", response_model=list[WorkspaceDigestRead])
def list_digests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    digests = session.exec(
        select(WorkspaceDigest).where(WorkspaceDigest.owner_id == current_user.id).order_by(WorkspaceDigest.generated_at.desc())
    ).all()
    return [WorkspaceDigestRead(**digest_to_read(digest)) for digest in digests]


@router.post("/digests/{digest_id}/deliver", response_model=DigestDeliveryRead)
def deliver_workspace_digest(
    digest_id: int,
    payload: DigestDeliveryRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    digest = session.get(WorkspaceDigest, digest_id)
    if not digest or digest.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Digest not found")
    try:
        result = deliver_digest(session, digest=digest, target=payload.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DigestDeliveryRead(**result)
