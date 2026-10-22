"""Household routers: create/list/cancel pickup requests."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PickupRequest
from app.schemas import CancelBody, RequestCreate, RequestDetail, RequestOut
from app.services.core import get_household_or_404, get_request_or_404, household_cancel

router = APIRouter(tags=["household"])


@router.post("/requests", response_model=RequestOut, status_code=201)
def create_request(body: RequestCreate, db: Session = Depends(get_db)):
    """Household posts a new pickup request (ownership: household_id in body)."""
    get_household_or_404(db, body.household_id)  # 404 if unknown household
    obj = PickupRequest(
        household_id=body.household_id,
        material_type=body.material_type,
        estimated_weight_kg=body.estimated_weight_kg,
        area=body.area,
        address_note=body.address_note,
        preferred_time=body.preferred_time,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/households/{household_id}/requests", response_model=list[RequestOut])
def household_requests(household_id: int, db: Session = Depends(get_db)):
    get_household_or_404(db, household_id)
    return (
        db.query(PickupRequest)
        .filter(PickupRequest.household_id == household_id)
        .order_by(PickupRequest.created_at.desc())
        .all()
    )


@router.get("/requests/{request_id}", response_model=RequestDetail)
def get_request(request_id: int, db: Session = Depends(get_db)):
    return get_request_or_404(db, request_id)


@router.post("/requests/{request_id}/cancel", response_model=RequestOut)
def cancel_request(request_id: int, body: CancelBody, db: Session = Depends(get_db)):
    """Owning household cancels an Available request."""
    return household_cancel(db, request_id, body.household_id, body.reason)
