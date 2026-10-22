"""Seed sample data: 5 households, 4 collectors, ~20 requests across statuses.

Run from backend/:  .venv/bin/python seed.py   (or: python seed.py)
"""
import random
from datetime import timedelta

from app.database import SessionLocal, init_db
from app.models import (
    ACCEPTED,
    AVAILABLE,
    CANCELLED,
    COMPLETED,
    FAILED,
    CollectionRecord,
    Collector,
    Household,
    PickupRequest,
    utcnow,
)
from app.services.core import variance_kg, variance_percent


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        # Idempotent: skip if data already present.
        if db.query(Household).count() > 0:
            print("Seed data already present — skipping. Delete recycling.db to reseed.")
            return

        households = [
            Household(name="Ananya Rao", phone="9876543210", area="Koramangala"),
            Household(name="Farhan Sheikh", phone="9876543211", area="Indiranagar"),
            Household(name="Meera Pillai", phone="9876543212", area="Whitefield"),
            Household(name="Vikram Shetty", phone="9876543213", area="Jayangar"),
            Household(name="Lakshmi Iyer", phone="9876543214", area="HSR Layout"),
        ]
        db.add_all(households)

        collectors = [
            Collector(name="GreenCycle Collectives", phone="9880000001",
                      accepted_materials=["Paper", "Cardboard"], service_areas=["Koramangala", "HSR Layout"],
                      max_capacity_kg=200, active=True),
            Collector(name="BinFirst Services", phone="9880000002",
                      accepted_materials=["Plastic", "Metal", "Glass"], service_areas=["Indiranagar", "Koramangala"],
                      max_capacity_kg=150, active=True),
            Collector(name="EcoKabadi", phone="9880000003",
                      accepted_materials=["Mixed", "Paper", "Plastic"], service_areas=["Whitefield", "Jayangar", "HSR Layout"],
                      max_capacity_kg=None, active=True),
            Collector(name="Metro E-waste", phone="9880000004",
                      accepted_materials=["E-waste", "Metal"], service_areas=["Whitefield", "Indiranagar"],
                      max_capacity_kg=80, active=False),  # inactive example
        ]
        db.add_all(collectors)
        db.commit()

        now = utcnow
        rng = random.Random(42)

        # 20 requests spread across statuses.
        materials = ["Paper", "Plastic", "Metal", "Glass", "E-waste", "Cardboard", "Mixed"]
        created = []
        for i in range(20):
            hh = households[i % 5]
            material = materials[i % 7]
            req = PickupRequest(
                household_id=hh.id,
                material_type=material,
                estimated_weight_kg=round(rng.uniform(2, 40), 1),
                area=hh.area,
                address_note=f"Gate {rng.randint(1, 9)}, {hh.area}",
                preferred_time=["Morning", "Afternoon", "Evening"][i % 3],
            )
            created.append(req)
        db.add_all(created)
        db.commit()

        # Assign statuses deterministically: 8 available, 4 accepted, 5 completed, 2 cancelled, 1 failed.
        for i, req in enumerate(created):
            req.created_at = now() - timedelta(days=14 - i, hours=rng.randint(0, 20))
            if i < 8:      # Available
                req.status = AVAILABLE
            elif i < 12:   # Accepted
                req.status = ACCEPTED
                req.accepted_at = req.created_at + timedelta(hours=6)
                req.collector_id = collectors[i % 3].id
            elif i < 17:   # Completed
                req.status = COMPLETED
                req.accepted_at = req.created_at + timedelta(hours=6)
                req.completed_at = req.created_at + timedelta(days=1)
                req.collector_id = collectors[i % 3].id
                actual = round(req.estimated_weight_kg * rng.uniform(0.85, 1.15), 1)
                req.collection_record = CollectionRecord(
                    request_id=req.id,
                    collector_id=req.collector_id,
                    actual_weight_kg=actual,
                    variance_kg=variance_kg(actual, req.estimated_weight_kg),
                    variance_percent=variance_percent(actual, req.estimated_weight_kg),
                    notes="Seeded sample record",
                )
            elif i < 19:   # Cancelled
                req.status = CANCELLED
                req.cancel_reason = "Household found another way to dispose"
            else:          # Failed
                req.status = ACCEPTED
                req.collector_id = collectors[0].id
                req.accepted_at = req.created_at + timedelta(hours=6)
                db.flush()
                req.status = FAILED
                req.failure_reason = "Access to building blocked"
        db.commit()
        print(f"Seeded {len(households)} households, {len(collectors)} collectors, {len(created)} pickup requests.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
