"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import MATERIALS

MaterialType = Literal["Paper", "Plastic", "Metal", "Glass", "E-waste", "Cardboard", "Mixed"]


# ---------- Profiles ----------
class HouseholdCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=32)
    area: str = Field(min_length=1, max_length=120)


class HouseholdOut(HouseholdCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class CollectorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=32)
    accepted_materials: list[MaterialType] = Field(min_length=1)
    service_areas: list[str] = Field(min_length=1)
    max_capacity_kg: Optional[float] = Field(default=None, gt=0, le=1000)

    @field_validator("service_areas")
    @classmethod
    def strip_areas(cls, v: list[str]) -> list[str]:
        out = [a.strip() for a in v if a.strip()]
        if not out:
            raise ValueError("service_areas must contain at least one non-empty area")
        return out


class CollectorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, min_length=5, max_length=32)
    accepted_materials: Optional[list[MaterialType]] = None
    service_areas: Optional[list[str]] = None
    max_capacity_kg: Optional[float] = Field(default=None, gt=0, le=1000)
    active: Optional[bool] = None


class CollectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str
    accepted_materials: list
    service_areas: list
    max_capacity_kg: Optional[float]
    active: bool
    created_at: datetime


# ---------- Pickup requests ----------
class RequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    household_id: int
    material_type: MaterialType
    estimated_weight_kg: float = Field(gt=0, le=1000)
    area: str = Field(min_length=1, max_length=120)
    address_note: Optional[str] = Field(default=None, max_length=255)
    preferred_time: Optional[str] = Field(default=None, max_length=64)


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    household_id: int
    material_type: str
    estimated_weight_kg: float
    area: str
    address_note: Optional[str]
    preferred_time: Optional[str]
    status: str
    collector_id: Optional[int]
    created_at: datetime
    accepted_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancel_reason: Optional[str]
    failure_reason: Optional[str]


class RequestDetail(RequestOut):
    household: HouseholdOut
    collector: Optional[CollectorOut]
    collection_record: Optional["CollectionRecordOut"]


class CancelBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    household_id: int
    reason: Optional[str] = Field(default=None, max_length=255)


# ---------- Collector actions ----------
class ClaimBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    collector_id: int


class CompleteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    collector_id: int
    actual_weight_kg: float = Field(gt=0, le=1000)
    notes: Optional[str] = Field(default=None, max_length=255)


class ReasonBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    collector_id: int
    reason: str = Field(min_length=1, max_length=255)


class CollectionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    request_id: int
    collector_id: int
    actual_weight_kg: float
    variance_kg: float
    variance_percent: float
    notes: Optional[str]
    recorded_at: datetime


# ---------- Stats ----------
RequestDetail.model_rebuild()


class StatusCounts(BaseModel):
    Available: int = 0
    Accepted: int = 0
    Completed: int = 0
    Cancelled: int = 0
    Failed: int = 0


class SummaryStats(BaseModel):
    total_completed: int
    total_actual_kg_by_material: dict[str, float]
    average_variance_percent: Optional[float]
    matching_accuracy_percent: float
    status_counts: StatusCounts
