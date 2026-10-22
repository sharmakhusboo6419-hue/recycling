"""Tests: state machine, validation, matching, ownership, variance, atomic claim."""
import threading
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.conftest import make_request  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import ACCEPTED, AVAILABLE, COMPLETED, CollectionRecord, Collector, Household  # noqa: E402
from app.services.core import variance_kg, variance_percent  # noqa: E402


# ---------------- Validation ----------------
def test_create_request_validation_errors(client):
    # bad material
    r = client.post("/requests", json={"household_id": 1, "material_type": "Nuclear",
                                       "estimated_weight_kg": 5, "area": "Koramangala"})
    assert r.status_code == 422
    # zero / over-max weight
    r = client.post("/requests", json={"household_id": 1, "material_type": "Paper",
                                       "estimated_weight_kg": 0, "area": "Koramangala"})
    assert r.status_code == 422
    r = client.post("/requests", json={"household_id": 1, "material_type": "Paper",
                                       "estimated_weight_kg": 2000, "area": "Koramangala"})
    assert r.status_code == 422
    # missing area
    r = client.post("/requests", json={"household_id": 1, "material_type": "Paper",
                                       "estimated_weight_kg": 5})
    assert r.status_code == 422
    # unknown household -> 404
    r = client.post("/requests", json={"household_id": 9999, "material_type": "Paper",
                                       "estimated_weight_kg": 5, "area": "Koramangala"})
    assert r.status_code == 404


def test_create_request_ok(client):
    r = client.post("/requests", json={"household_id": 1, "material_type": "Paper",
                                       "estimated_weight_kg": 12.5, "area": "koramangala",
                                       "address_note": "Flat 3B"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "Available" and body["material_type"] == "Paper"


# ---------------- Matching rules ----------------
def test_matching_rules(client, db):
    # eligible: Paper + Koramangala
    req = make_request(db, material_type="Paper", area="Koramangala")
    avail = client.get("/collectors/1/available-requests").json()
    assert any(r["id"] == req.id for r in avail)
    # ineligible: wrong material
    req2 = make_request(db, material_type="Plastic", area="Koramangala")
    avail = client.get("/collectors/1/available-requests").json()
    assert not any(r["id"] == req2.id for r in avail)
    # ineligible: wrong area (case-insensitive area match still works)
    req3 = make_request(db, material_type="Paper", area="Indiranagar")
    avail = client.get("/collectors/1/available-requests").json()
    assert not any(r["id"] == req3.id for r in avail)
    # inactive collector never eligible
    req4 = make_request(db, material_type="Paper", area="Koramangala")
    assert client.get("/collectors/3/available-requests").json() == []
    # capacity: request heavier than collector max
    req5 = make_request(db, material_type="Paper", area="Koramangala", estimated_weight_kg=500)
    avail = client.get("/collectors/1/available-requests").json()
    assert not any(r["id"] == req5.id for r in avail)


def test_ineligible_claim_403(client, db):
    req = make_request(db, material_type="Plastic", area="Indiranagar")
    r = client.post(f"/requests/{req.id}/claim", json={"collector_id": 1})
    assert r.status_code == 403


# ---------------- Claim + concurrency ----------------
def test_single_claim_succeeds(client, db):
    req = make_request(db)
    r = client.post(f"/requests/{req.id}/claim", json={"collector_id": 1})
    assert r.status_code == 200 and r.json()["status"] == "Accepted"
    # second claim -> 409 Already claimed
    r2 = client.post(f"/requests/{req.id}/claim", json={"collector_id": 1})
    assert r2.status_code == 409
    assert "Already claimed" in r2.json()["detail"]


def test_concurrent_claims_exactly_one_succeeds(client, db):
    req = make_request(db, estimated_weight_kg=5)
    results = []

    def try_claim():
        # Each thread gets its own DB session + HTTP client to simulate true
        # concurrency against the same SQLite file.
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            resp = c.post(f"/requests/{req.id}/claim", json={"collector_id": 1})
            results.append(resp.status_code)

    threads = [threading.Thread(target=try_claim) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = results.count(200)
    conflicts = results.count(409)
    assert successes == 1, f"expected exactly 1 success, got {results}"
    assert conflicts == 19
    db.expire_all()
    assert db.merge(req).status == "Accepted"


# ---------------- State machine ----------------
def test_state_machine_transitions(client, db):
    # Available -> Cancelled by owning household OK
    r1 = make_request(db)
    assert client.post(f"/requests/{r1.id}/cancel", json={"household_id": 1}).json()["status"] == "Cancelled"
    # Cancelled is terminal
    r = client.post(f"/requests/{r1.id}/cancel", json={"household_id": 1})
    assert r.status_code == 409

    # Accepted -> Completed
    r2 = make_request(db)
    assert client.post(f"/requests/{r2.id}/claim", json={"collector_id": 1}).json()["status"] == "Accepted"
    r = client.post(f"/requests/{r2.id}/complete",
                    json={"collector_id": 1, "actual_weight_kg": 9.0, "notes": "ok"})
    assert r.status_code == 200 and r.json()["status"] == "Completed"
    rec = client.get(f"/requests/{r2.id}").json()["collection_record"]
    assert rec["variance_kg"] == -1.0 and rec["variance_percent"] == -10.0
    # Completed is terminal
    assert client.post(f"/requests/{r2.id}/claim", json={"collector_id": 1}).status_code == 409

    # Accepted -> Failed by assigned collector
    r3 = make_request(db)
    client.post(f"/requests/{r3.id}/claim", json={"collector_id": 1})
    r = client.post(f"/requests/{r3.id}/fail", json={"collector_id": 1, "reason": "No access"})
    assert r.status_code == 200 and r.json()["status"] == "Failed"
    # Failed is terminal
    assert client.post(f"/requests/{r3.id}/complete",
                       json={"collector_id": 1, "actual_weight_kg": 1}).status_code == 409

    # Accepted -> Cancelled by collector
    r4 = make_request(db)
    client.post(f"/requests/{r4.id}/claim", json={"collector_id": 1})
    r = client.post(f"/requests/{r4.id}/collector-cancel", json={"collector_id": 1, "reason": "Off duty"})
    assert r.status_code == 200 and r.json()["status"] == "Cancelled"


def test_ownership_checks(client, db):
    req = make_request(db)
    # create a second household so "42" is a real profile owning nothing
    other = Household(name="Other Home", phone="9000000042", area="Indiranagar")
    db.add(other)
    db.commit()
    # wrong household cancels -> 403
    r = client.post(f"/requests/{req.id}/cancel", json={"household_id": other.id})
    assert r.status_code == 403
    # nonexistent household -> 404
    r = client.post(f"/requests/{req.id}/cancel", json={"household_id": 777})
    assert r.status_code == 404

    # claim by collector 1, then collector 2 (unassigned) tries complete -> 403
    client.post(f"/requests/{req.id}/claim", json={"collector_id": 1})
    r = client.post(f"/requests/{req.id}/complete", json={"collector_id": 2, "actual_weight_kg": 1})
    assert r.status_code == 403
    # unknown collector -> 404
    r = client.post(f"/requests/{req.id}/complete", json={"collector_id": 999, "actual_weight_kg": 1})
    assert r.status_code == 404
    # unknown request id -> 404
    assert client.get("/requests/99999").status_code == 404


# ---------------- Variance maths ----------------
def test_variance_maths():
    assert variance_kg(12.0, 10.0) == 2.0
    assert variance_percent(12.0, 10.0) == 20.0
    assert variance_percent(9.0, 10.0) == -10.0
    assert variance_percent(10.0, 10.0) == 0.0


# ---------------- Stats ----------------
def test_stats_summary(client, db):
    req = make_request(db, material_type="Metal")
    client.post(f"/requests/{req.id}/claim", json={"collector_id": 1})
    client.post(f"/requests/{req.id}/complete", json={"collector_id": 1, "actual_weight_kg": 11.0})
    stats = client.get("/stats/summary").json()
    assert stats["total_completed"] >= 1
    assert stats["status_counts"]["Completed"] >= 1
    assert isinstance(stats["total_actual_kg_by_material"], dict)
    assert stats["average_variance_percent"] is not None
    assert 0 <= stats["matching_accuracy_percent"] <= 100
