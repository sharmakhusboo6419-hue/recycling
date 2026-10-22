"""Stats router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SummaryStats
from app.services.core import summary_stats

router = APIRouter(tags=["stats"])


@router.get("/stats/summary", response_model=SummaryStats)
def get_summary(db: Session = Depends(get_db)):
    return summary_stats(db)
