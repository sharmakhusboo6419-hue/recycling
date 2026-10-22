"""SQLAlchemy ORM models for the Recycling Pickup Exchange."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Request lifecycle statuses (strict state machine, see services/state.py).
AVAILABLE = "Available"
ACCEPTED = "Accepted"
COMPLETED = "Completed"
CANCELLED = "Cancelled"
FAILED = "Failed"

# Material enum values.
MATERIALS = ["Paper", "Plastic", "Metal", "Glass", "E-waste", "Cardboard", "Mixed"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Household(Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    area: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    requests: Mapped[list["PickupRequest"]] = relationship(back_populates="household")


class Collector(Base):
    __tablename__ = "collectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    accepted_materials: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    service_areas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    max_capacity_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class PickupRequest(Base):
    __tablename__ = "pickup_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), nullable=False)
    material_type: Mapped[str] = mapped_column(String(32), nullable=False)
    estimated_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    area: Mapped[str] = mapped_column(String(120), nullable=False)
    address_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=AVAILABLE, nullable=False, index=True)
    collector_id: Mapped[int | None] = mapped_column(ForeignKey("collectors.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    household: Mapped[Household] = relationship(back_populates="requests")
    collector: Mapped[Collector | None] = relationship()
    collection_record: Mapped["CollectionRecord | None"] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )


class CollectionRecord(Base):
    __tablename__ = "collection_records"
    __table_args__ = (UniqueConstraint("request_id", name="uq_collection_record_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("pickup_requests.id"), nullable=False)
    collector_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"), nullable=False)
    actual_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    variance_kg: Mapped[float] = mapped_column(Float, nullable=False)
    variance_percent: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    request: Mapped[PickupRequest] = relationship(back_populates="collection_record")
