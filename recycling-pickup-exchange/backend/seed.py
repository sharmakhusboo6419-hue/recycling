"""Seed sample data for the Recycling Pickup Exchange.

Run from backend/:  .venv/bin/python seed.py   (or: python seed.py)

The dataset is curated so the collector-matching rules are easy to demo.
A collector only sees a request when ALL of these hold:
  1. material_type is in the collector's accepted_materials
  2. area is in the collector's service_areas (case-insensitive)
  3. the collector is active
  4. estimated weight is within the collector's max_capacity_kg (if set)
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
                      max_capacity_kg=100, active=True),
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

        # ------------------------------------------------------------------
        # Curated pickup requests — the demo story.
        #
        # Every active collector gets at least one claimable "Available"
        # request, and three requests exist purely to demonstrate each
        # matching-exclusion rule (see EXPLAIN.md-style walkthrough below):
        #
        #   GreenCycle (Paper/Cardboard, Koramangala+HSR, cap 100kg)
        #     sees: Paper 12.5kg Koramangala, Cardboard 22kg HSR, Paper 9.3kg HSR
        #   BinFirst (Plastic/Metal/Glass, Indiranagar+Koramangala, cap 150kg)
        #     sees: Plastic 30.2kg Indiranagar, Metal 8.4kg Koramangala
        #   EcoKabadi (Mixed/Paper/Plastic, Whitefield+Jayanagar+HSR, no cap)
        #     sees: Mixed 15kg Whitefield, Plastic 18.7kg Jayanagar, Paper 9.3kg HSR
        #
        #   EXCLUDED (nobody can claim):
        #     • Glass 11.6kg Whitefield  → material not in Metro's list AND
        #       Metro is inactive; area not served by BinFirst/EcoKabadi
        #     • Paper 120kg Koramangala  → over GreenCycle's 100kg capacity
        #     • E-waste 6kg Whitefield   → only Metro accepts E-waste, inactive
        # ------------------------------------------------------------------
        spec = [
            # (household, material, est_kg, area, note, preferred)
            (0, "Paper",     12.5, "Koramangala", "Flat 402, 5th Block — ask security for Gate 2", "Morning"),
            (4, "Cardboard", 22.0, "HSR Layout",  "Moving boxes stacked in the lobby", "Afternoon"),
            (1, "Plastic",   30.2, "Indiranagar", "Bags of bottles, rear balcony", "Evening"),
            (0, "Metal",      8.4, "Koramangala", "Old utensils and a broken grill", "Morning"),
            (2, "Mixed",     15.0, "Whitefield",  "General dry waste, mixed bag", "Morning"),
            (3, "Plastic",   18.7, "Jayanagar",   "Weekly plastic collection", "Afternoon"),
            (4, "Paper",      9.3, "HSR Layout",  "Newspapers and magazines", "Evening"),
            # -- exclusions --
            (2, "Glass",     11.6, "Whitefield",  "Jars and bottles, handle with care", "Afternoon"),
            (0, "Paper",    120.0, "Koramangala", "Office clearance — very heavy load", "Morning"),
            (2, "E-waste",    6.0, "Whitefield",  "Old monitor and keyboard", "Evening"),
        ]
        created = []
        for i, (hi, m, w, a, n, t) in enumerate(spec):
            req = PickupRequest(
                household_id=households[hi].id,
                material_type=m,
                estimated_weight_kg=w,
                area=a,
                address_note=n,
                preferred_time=t,
            )
            created.append(req)
        db.add_all(created)
        db.commit()

        # Timestamps: Available requests are recent, so the demo lists look live.
        for i, req in enumerate(created):
            req.created_at = now() - timedelta(days=10 - i, hours=rng.randint(0, 20))
        db.commit()

        # ------------------------------------------------------------------
        # Accepted requests — assigned to collectors who are genuinely
        # eligible, showing the "claimed" stage of the lifecycle.
        # ------------------------------------------------------------------
        accepted = [
            PickupRequest(
                household_id=households[1].id, material_type="Glass",
                estimated_weight_kg=24.4, area="Indiranagar",
                address_note="House 12, 100 Feet Road", preferred_time="Evening",
                status=ACCEPTED, collector_id=collectors[1].id),   # BinFirst
            PickupRequest(
                household_id=households[3].id, material_type="Mixed",
                estimated_weight_kg=14.2, area="Jayanagar",
                address_note="3rd Cross, near the park", preferred_time="Morning",
                status=ACCEPTED, collector_id=collectors[2].id),   # EcoKabadi
            PickupRequest(
                household_id=households[0].id, material_type="Cardboard",
                estimated_weight_kg=45.0, area="Koramangala",
                address_note="Flat 402, 5th Block", preferred_time="Afternoon",
                status=ACCEPTED, collector_id=collectors[0].id),   # GreenCycle
            PickupRequest(
                household_id=households[4].id, material_type="Plastic",
                estimated_weight_kg=10.8, area="HSR Layout",
                address_note="Gate 3, Sector 2", preferred_time="Morning",
                status=ACCEPTED, collector_id=collectors[2].id),   # EcoKabadi
        ]
        for r in accepted:
            r.created_at = now() - timedelta(days=5, hours=rng.randint(0, 20))
            r.accepted_at = r.created_at + timedelta(hours=6)

        # ------------------------------------------------------------------
        # Completed requests — each carries a CollectionRecord with variance
        # so estimated-vs-actual and the stats page have real data. Actual
        # weight varies ±15% around the estimate, producing a mix of
        # within-±10% (accurate) and outside-±10% results.
        # ------------------------------------------------------------------
        completed = [
            (0, "Paper",     20.0, "Koramangala", "Flat 402, 5th Block", "Morning", 0),
            (1, "Plastic",   12.0, "Indiranagar", "House 12, 100 Feet Road", "Evening", 1),
            (3, "Metal",      5.0, "Jayanagar",   "3rd Cross, near the park", "Afternoon", 1),
            (2, "Mixed",     13.0, "Whitefield",  "Prestige Shantiniketan, Tower B", "Morning", 2),
            (4, "Cardboard", 35.0, "HSR Layout",  "Gate 3, Sector 2", "Afternoon", 0),
            (1, "Plastic",    9.0, "Indiranagar", "House 12, 100 Feet Road", "Morning", 2),
            (3, "Paper",     16.0, "Jayanagar",   "3rd Cross, near the park", "Evening", 2),
        ]
        notes = ["Weight from the scale at pickup",
                 "Household added an extra bag at the door",
                 "Only dry, clean items accepted"]
        for i, (hi, m, w, a, n, t, ci) in enumerate(completed):
            r = PickupRequest(
                household_id=households[hi].id, material_type=m,
                estimated_weight_kg=w, area=a, address_note=n, preferred_time=t,
                status=COMPLETED, collector_id=collectors[ci].id)
            r.created_at = now() - timedelta(days=12 - i, hours=rng.randint(0, 20))
            r.accepted_at = r.created_at + timedelta(hours=6)
            r.completed_at = r.created_at + timedelta(days=1)
            actual = round(w * rng.uniform(0.85, 1.15), 1)
            r.collection_record = CollectionRecord(
                request_id=r.id, collector_id=collectors[ci].id,
                actual_weight_kg=actual,
                variance_kg=variance_kg(actual, w),
                variance_percent=variance_percent(actual, w),
                notes=notes[i % 3])
            db.add(r)

        # Cancelled (household / collector) and Failed, with reasons.
        cancelled = [
            PickupRequest(
                household_id=households[2].id, material_type="Glass",
                estimated_weight_kg=7.5, area="Whitefield",
                address_note="Prestige Shantiniketan, Tower B", preferred_time="Morning",
                status=CANCELLED, cancel_reason="Household found another way to dispose"),
            PickupRequest(
                household_id=households[0].id, material_type="Mixed",
                estimated_weight_kg=6.8, area="Koramangala",
                address_note="Flat 402, 5th Block", preferred_time="Evening",
                status=CANCELLED, cancel_reason="Duplicates — combined into another request"),
        ]
        for r in cancelled:
            r.created_at = now() - timedelta(days=8, hours=rng.randint(0, 20))

        failed = PickupRequest(
            household_id=households[4].id, material_type="Paper",
            estimated_weight_kg=11.0, area="HSR Layout",
            address_note="Gate 3, Sector 2", preferred_time="Morning",
            status=FAILED, collector_id=collectors[0].id,
            failure_reason="Access to building blocked — no one at the gate")
        failed.created_at = now() - timedelta(days=6)
        failed.accepted_at = failed.created_at + timedelta(hours=6)

        db.add_all(accepted + cancelled + [failed])
        db.commit()

        print(f"Seeded {len(households)} households, {len(collectors)} collectors, "
              f"{len(created) + len(accepted) + len(completed) + len(cancelled) + 1} pickup requests "
              f"({len(created)} Available, {len(accepted)} Accepted, {len(completed)} Completed, "
              f"{len(cancelled)} Cancelled, 1 Failed).")
        print("Matching demo guide (who sees what among Available):")
        print("  GreenCycle Collectives -> Paper 12.5kg Koramangala, Cardboard 22kg HSR, Paper 9.3kg HSR")
        print("  BinFirst Services      -> Plastic 30.2kg Indiranagar, Metal 8.4kg Koramangala")
        print("  EcoKabadi              -> Mixed 15kg Whitefield, Plastic 18.7kg Jayanagar, Paper 9.3kg HSR")
        print("  Nobody sees: Glass 11.6kg Whitefield (area/material mismatch), Paper 120kg "
              "Koramangala (over capacity), E-waste 6kg Whitefield (collector inactive)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
