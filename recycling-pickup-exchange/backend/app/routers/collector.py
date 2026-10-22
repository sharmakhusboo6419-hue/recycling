"""Collector routers: eligible available list, claim, complete, fail, cancel."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ACCEPTED, COMPLETED, PickupRequest
from app.schemas import ClaimBody, CompleteBody, ReasonBody, RequestOut
from app.services.core import (
    claim_request,
    collector_cancel,
    complete_request,
    eligible_available_requests,
    fail_request,
    get_collector_or_404,
)

router = APIRouter(tags=["collector"])


@router.get("/collectors/{collector_id}/available-requests", response_model=list[RequestOut])
def available_requests(collector_id: int, db: Session = Depends(get_db)):
    """Available requests matching this collector's materials/areas/capacity."""
    return eligible_available_requests(db, collector_id)


@router.post("/requests/{request_id}/claim", response_model=RequestOut)
def claim(request_id: int, body: ClaimBody, db: Session = Depends(get_db)):
    """Atomic claim: exactly one collector wins; others get 409 'Already claimed'."""
    return claim_request(db, request_id, body.collector_id)


@router.get("/collectors/{collector_id}/requests", response_model=list[RequestOut])
def collector_requests(collector_id: int, status: str | None = None, db: Session = Depends(get_db)):
    """Requests assigned to this collector; optional status filter (Accepted|Completed|Failed...)."""
    get_collector_or_404(db, collector_id)
    q = db.query(PickupRequest).filter(PickupRequest.collector_id == collector_id)
    if status:
        q = q.filter(PickupRequest.status == status)
    return q.order_by(PickupRequest.created_at.desc()).all()


@router.post("/requests/{request_id}/complete", response_model=RequestOut)
def complete(request_id: int, body: CompleteBody, db: Session = Depends(get_db)):
    """Assigned collector confirms pickup with the actual collected quantity."""
    return complete_request(db, request_id, body.collector_id, body.actual_weight_kg, body.notes)


@router.post("/requests/{request_id}/fail", response_model=RequestOut)
def fail(request_id: int, body: ReasonBody, db: Session = Depends(get_db)):
    return fail_request(db, request_id, body.collector_id, body.reason)


@router.post("/requests/{request_id}/collector-cancel", response_model=RequestOut)
def collector_cancel_route(request_id: int, body: ReasonBody, db: Session = Depends(get_db)):
    return collector_cancel(db, request_id, body.collector_id, body.reason)
