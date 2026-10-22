"""Shared pytest fixtures. Uses an isolated temp SQLite DB per test session."""
import os
import sys
import tempfile

# Ensure the backend directory (parent of tests/) is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# Point DATABASE_URL at a temp file BEFORE importing app modules.
_tmpdir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"

from app.main import app  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import (  # noqa: E402
    ACCEPTED,
    AVAILABLE,
    COMPLETED,
    CollectionRecord,
    Collector,
    Household,
    PickupRequest,
)
from app import models as m  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _seed_db():
    init_db()
    db = SessionLocal()
    hh = Household(name="Test Home", phone="9000000000", area="Koramangala")
    db.add(hh)
    db.flush()
    c1 = Collector(name="Paper Guy", phone="9000000001", accepted_materials=["Paper", "Cardboard"],
                   service_areas=["Koramangala"], max_capacity_kg=100, active=True)
    c2 = Collector(name="Plastic Guy", phone="9000000002", accepted_materials=["Plastic"],
                   service_areas=["Indiranagar"], active=True)
    c3 = Collector(name="Sleepy Guy", phone="9000000003", accepted_materials=["Paper"],
                   service_areas=["Koramangala"], active=False)
    db.add_all([c1, c2, c3])
    db.commit()
    db.close()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def make_request(db, **overrides):
    data = dict(household_id=1, material_type="Paper", estimated_weight_kg=10.0,
                area="Koramangala")
    data.update(overrides)
    req = PickupRequest(**data)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req
