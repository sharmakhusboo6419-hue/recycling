"""Profile routers: households and collectors."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Collector, Household
from app.schemas import CollectorCreate, CollectorOut, CollectorUpdate, HouseholdCreate, HouseholdOut
from app.services.core import get_collector_or_404

router = APIRouter(tags=["profiles"])


@router.get("/households", response_model=list[HouseholdOut])
def list_households(db: Session = Depends(get_db)):
    return db.query(Household).order_by(Household.id).all()


@router.post("/households", response_model=HouseholdOut, status_code=201)
def create_household(body: HouseholdCreate, db: Session = Depends(get_db)):
    obj = Household(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/collectors", response_model=list[CollectorOut])
def list_collectors(db: Session = Depends(get_db)):
    return db.query(Collector).order_by(Collector.id).all()


@router.post("/collectors", response_model=CollectorOut, status_code=201)
def create_collector(body: CollectorCreate, db: Session = Depends(get_db)):
    obj = Collector(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/collectors/{collector_id}", response_model=CollectorOut)
def get_collector(collector_id: int, db: Session = Depends(get_db)):
    return get_collector_or_404(db, collector_id)


@router.put("/collectors/{collector_id}", response_model=CollectorOut)
def update_collector(collector_id: int, body: CollectorUpdate, db: Session = Depends(get_db)):
    obj = get_collector_or_404(db, collector_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj
