"""Core domain services: matching, atomic claim, completion/variance, stats."""
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    ACCEPTED,
    AVAILABLE,
    COMPLETED,
    CollectionRecord,
    Collector,
    Household,
    MATERIALS,
    PickupRequest,
    utcnow,
)

# Message constants (single source of truth shared with tests).
ALREADY_CLAIMED = "Already claimed: this request has been claimed by another collector."


# ---------------------------------------------------------------------------
# Ownership / role validation helpers
# ---------------------------------------------------------------------------
def get_household_or_404(db: Session, household_id: int) -> Household:
    obj = db.get(Household, household_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Household not found.")
    return obj


def get_collector_or_404(db: Session, collector_id: int) -> Collector:
    obj = db.get(Collector, collector_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Collector not found.")
    return obj


def get_request_or_404(db: Session, request_id: int) -> PickupRequest:
    obj = db.get(PickupRequest, request_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Pickup request not found.")
    return obj


# ---------------------------------------------------------------------------
# Matching rules
# ---------------------------------------------------------------------------
def is_eligible(collector: Collector, request: PickupRequest) -> bool:
    """Rule-based match: material in accepted_materials AND area in
    service_areas (case-insensitive) AND active AND weight within capacity."""
    if not collector.active:
        return False
    if request.material_type not in MATERIALS:
        return False
    if request.material_type.lower() not in (m.lower() for m in collector.accepted_materials):
        return False
    if request.area.lower() not in (a.lower() for a in collector.service_areas):
        return False
    if collector.max_capacity_kg is not None and request.estimated_weight_kg > collector.max_capacity_kg:
        return False
    return True


def eligible_available_requests(db: Session, collector_id: int) -> list[PickupRequest]:
    """All Available requests that this collector is eligible to claim."""
    collector = get_collector_or_404(db, collector_id)
    requests = (
        db.query(PickupRequest)
        .filter(PickupRequest.status == AVAILABLE)
        .order_by(PickupRequest.created_at.desc())
        .all()
    )
    return [r for r in requests if is_eligible(collector, r)]


# ---------------------------------------------------------------------------
# Atomic single-collector claim
# ---------------------------------------------------------------------------
def claim_request(db: Session, request_id: int, collector_id: int) -> PickupRequest:
    """Atomically claim a request with a single conditional UPDATE.

    Uses BEGIN IMMEDIATE on SQLite so that concurrent claims from multiple
    threads/processes serialise: exactly one UPDATE matches
    `status='Available'` (rowcount 1); all others see 0 and raise 409.
    """
    collector = get_collector_or_404(db, collector_id)
    request = get_request_or_404(db, request_id)  # raises 404 if unknown id

    # Rule check BEFORE attempting the write so ineligible collectors get 403
    # even if the request is still Available.
    if not is_eligible(collector, request):
        raise HTTPException(
            status_code=403,
            detail="Not eligible: the request's material or area is not in your "
                   "accepted materials / service areas, or you are inactive/at capacity.",
        )

    conn = db.connection()  # DBAPI connection of this session's transaction
    dbapi = conn.connection.dbapi_connection
    is_sqlite = isinstance(dbapi, sqlite3.Connection)

    if is_sqlite:
        # Close any open python-sqlite3 transaction, then take the write lock
        # immediately so concurrent claims serialise (BEGIN IMMEDIATE).
        if dbapi.in_transaction:
            dbapi.commit()
        dbapi.execute("BEGIN IMMEDIATE")
    try:
        cur = dbapi.execute(
            "UPDATE pickup_requests "
            "SET status='Accepted', collector_id=?, accepted_at=? "
            "WHERE id=? AND status='Available'",
            (collector_id, datetime.now(timezone.utc).isoformat(), request_id),
        )
        rowcount = cur.rowcount
        cur.close()
        if is_sqlite:
            dbapi.commit()
    except Exception:
        if is_sqlite:
            try:
                dbapi.rollback()
            except Exception:
                pass
        raise
    finally:
        if is_sqlite:
            # Resync SQLAlchemy's view of the connection (it holds a logical
            # transaction that we just terminated at the DBAPI level).
            try:
                db.rollback()
            except Exception:
                pass

    if rowcount == 0:
        raise HTTPException(status_code=409, detail=ALREADY_CLAIMED)

    # Expire cached ORM state so the returned object reflects the UPDATE.
    db.expire_all()
    return get_request_or_404(db, request_id)


# ---------------------------------------------------------------------------
# Completion + variance
# ---------------------------------------------------------------------------
def complete_request(
    db: Session,
    request_id: int,
    collector_id: int,
    actual_weight_kg: float,
    notes: Optional[str] = None,
) -> PickupRequest:
    """Assigned collector confirms collection; stores actual kg + variance."""
    collector = get_collector_or_404(db, collector_id)
    request = get_request_or_404(db, request_id)

    if request.status != ACCEPTED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot complete a request in status '{request.status}'. Only Accepted requests can be completed.",
        )
    if request.collector_id != collector.id:
        raise HTTPException(status_code=403, detail="This request is assigned to another collector.")

    request.status = COMPLETED
    request.completed_at = utcnow()
    if request.collection_record is None:
        request.collection_record = CollectionRecord(
            request_id=request.id,
            collector_id=collector.id,
            actual_weight_kg=actual_weight_kg,
            variance_kg=variance_kg(actual_weight_kg, request.estimated_weight_kg),
            variance_percent=variance_percent(actual_weight_kg, request.estimated_weight_kg),
            notes=notes,
        )
    db.commit()
    db.refresh(request)
    return request


def variance_kg(actual: float, estimated: float) -> float:
    """variance_kg = actual - estimated."""
    return round(actual - estimated, 3)


def variance_percent(actual: float, estimated: float) -> float:
    """variance_percent = (variance_kg / estimated) * 100, rounded to 2dp."""
    return round((variance_kg(actual, estimated) / estimated) * 100, 2)


# ---------------------------------------------------------------------------
# State transitions (household cancel / collector cancel / fail)
# ---------------------------------------------------------------------------
def household_cancel(db: Session, request_id: int, household_id: int, reason: Optional[str]) -> PickupRequest:
    request = get_request_or_404(db, request_id)
    get_household_or_404(db, household_id)  # 404 for unknown household
    if request.household_id != household_id:
        raise HTTPException(status_code=403, detail="This request belongs to another household.")
    if request.status != AVAILABLE:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a request in status '{request.status}'. Only Available requests can be cancelled.",
        )
    request.status = "Cancelled"
    request.cancel_reason = reason or "Cancelled by household"
    db.commit()
    db.refresh(request)
    return request


def collector_cancel(db: Session, request_id: int, collector_id: int, reason: str) -> PickupRequest:
    collector = get_collector_or_404(db, collector_id)
    request = get_request_or_404(db, request_id)
    if request.collector_id != collector.id:
        raise HTTPException(status_code=403, detail="This request is assigned to another collector.")
    if request.status != ACCEPTED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a request in status '{request.status}'. Only Accepted requests can be cancelled.",
        )
    request.status = "Cancelled"
    request.cancel_reason = reason
    db.commit()
    db.refresh(request)
    return request


def fail_request(db: Session, request_id: int, collector_id: int, reason: str) -> PickupRequest:
    collector = get_collector_or_404(db, collector_id)
    request = get_request_or_404(db, request_id)
    if request.collector_id != collector.id:
        raise HTTPException(status_code=403, detail="This request is assigned to another collector.")
    if request.status != ACCEPTED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot fail a request in status '{request.status}'. Only Accepted requests can be marked failed.",
        )
    request.status = "Failed"
    request.failure_reason = reason
    db.commit()
    db.refresh(request)
    return request


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------
def summary_stats(db: Session) -> dict:
    total_completed = db.query(PickupRequest).filter(PickupRequest.status == COMPLETED).count()

    # total actual kg by material
    rows = (
        db.query(PickupRequest.material_type, CollectionRecord.actual_weight_kg)
        .join(CollectionRecord, PickupRequest.id == CollectionRecord.request_id)
        .all()
    )
    by_material: dict[str, float] = {m: 0.0 for m in MATERIALS}
    for material, actual in rows:
        by_material[material] = round(by_material.get(material, 0.0) + actual, 2)

    percents = [
        r[0]
        for r in db.query(CollectionRecord.variance_percent).all()
        if r[0] is not None
    ]
    avg_variance = round(sum(percents) / len(percents), 2) if percents else None
    accuracy = round(
        100.0 * len([p for p in percents if abs(p) <= 10.0]) / len(percents), 1
    ) if percents else 0.0

    status_counts = dict.fromkeys(
        ["Available", "Accepted", "Completed", "Cancelled", "Failed"], 0
    )
    for status, count in db.query(PickupRequest.status, text("count(*)")).group_by(PickupRequest.status).all():
        status_counts[status] = count

    return {
        "total_completed": total_completed,
        "total_actual_kg_by_material": by_material,
        "average_variance_percent": avg_variance,
        "matching_accuracy_percent": accuracy,
        "status_counts": status_counts,
    }
