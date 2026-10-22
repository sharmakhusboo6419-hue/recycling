# ♻️ Recycling Pickup Exchange

**Team Nexora — Tech Fusion 2026**

A responsive web platform that connects **households** with recyclable-waste **collectors**.
Households post pickup requests (material, estimated weight, area); eligible collectors claim
them — guaranteed **exactly one collector per request** via an atomic claim — then record the
actual collected quantity, and the system computes the **variance** against the estimate.

> No authentication by design: roles are demo profiles, and the API validates data ownership
> (household/collector id in the payload) with 403/404 — not authentication.

---

## Architecture

```
┌────────────────────────┐        ┌─────────────────────────────┐
│  React + Vite (5173)   │  JSON  │  FastAPI + Uvicorn (8000)   │
│  pages/ components/    │ ─────► │  routers/ services/         │
│  profileContext (role, │  CORS  │  Pydantic schemas           │
│  profile id → local-   │        │  ┌───────────────────────┐  │
│  Storage + state)      │        │  │ services/core.py      │  │
└────────────────────────┘        │  │ • rule-based matching │  │
                                  │  │ • atomic claim        │  │
                                  │  │   (BEGIN IMMEDIATE    │  │
                                  │  │    + rowcount check)  │  │
                                  │  │ • variance maths      │  │
                                  │  │ • summary stats       │  │
                                  │  └───────────────────────┘  │
                                  │      SQLAlchemy ORM         │
                                  │      ▼                      │
                                  │  SQLite (recycling.db)      │
                                  │  DATABASE_URL env → swap to │
                                  │  PostgreSQL later w/o code  │
                                  └─────────────────────────────┘
```

**State machine (strictly enforced, invalid transitions → HTTP 409):**

```
Available ──claim──► Accepted ──complete──► Completed
    │                    │ ├──collector-cancel──► Cancelled
    │                    └──fail─────────────► Failed
    └──household cancel──► Cancelled      (terminal states are immutable)
```

---

## Project structure

```
recycling-pickup-exchange/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, error handler
│   │   ├── database.py        # engine/session, env DATABASE_URL
│   │   ├── models.py          # households, collectors, pickup_requests, collection_records
│   │   ├── schemas.py         # Pydantic validation (422 on bad input)
│   │   ├── services/core.py   # matching, atomic claim, variance, transitions, stats
│   │   └── routers/           # profiles.py, household.py, collector.py, stats.py
│   ├── tests/                 # pytest incl. 20-thread concurrent-claim test
│   ├── seed.py                # sample data
│   ├── requirements.txt  .env.example  pytest.ini
└── frontend/
    └── src/
        ├── api.js             # fetch client with friendly error extraction
        ├── profileContext.jsx # acting profile → React state + localStorage
        ├── toastContext.jsx   # toasts
        ├── components/        # Header (switcher), RequestForm, RequestCard
        └── pages/             # ProfilePicker, HouseholdDashboard, CollectorDashboard,
                               # CollectorProfile, Stats
```

---

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional; defaults are fine for local dev
python seed.py                # seeds 5 households, 4 collectors, 20 requests
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: **http://localhost:8000/docs**

### Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

### Tests

```bash
cd backend
.venv/bin/python -m pytest -q
```

Covers: validation (422s), matching rules, ownership checks (403/404),
state-machine transitions + terminal-state rejection, variance maths,
single-claim semantics, and **20 simultaneous claims → exactly one 200, 19× 409**.

---

## API summary

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/households`, `/collectors` | list / create profiles |
| GET/PUT | `/collectors/{id}` | get / update collector (materials, areas, capacity, active) |
| POST | `/requests` | household posts a pickup request (422 on invalid material/weight) |
| GET | `/households/{id}/requests` | a household's requests |
| GET | `/requests/{id}` | full detail incl. household, collector, collection record |
| POST | `/requests/{id}/cancel` | owning household cancels while Available |
| GET | `/collectors/{id}/available-requests` | eligible Available requests only |
| POST | `/requests/{id}/claim` | atomic claim — 409 `Already claimed` for losers |
| GET | `/collectors/{id}/requests?status=` | accepted / history for a collector |
| POST | `/requests/{id}/complete` | record actual kg → stores variance |
| POST | `/requests/{id}/fail` | mark failed with reason |
| POST | `/requests/{id}/collector-cancel` | assigned collector cancels with reason |
| GET | `/stats/summary` | totals, kg by material, avg variance, matching accuracy, status counts |
| GET | `/health`, `/docs` | health check, OpenAPI UI |

Errors are always `{"detail": "<human-readable message>"}` with 403 / 404 / 409 / 422 / 500.

---

## Notes & assumptions

- **No auth** per the brief; the acting profile is passed explicitly and validated for
  existence + role + ownership.
- "Jayangar" spelling is used consistently in seed data (Bengaluru's Jayanagar, intentional
  single spelling so area matching is demo-predictable); matching is case-insensitive.
- Seed data is created on first `python seed.py` (idempotent — delete `backend/recycling.db`
  to reseed). The DB file is auto-created on backend startup even without seeding.
- The atomic claim uses `BEGIN IMMEDIATE` + a conditional `UPDATE` + `rowcount` on SQLite;
  on PostgreSQL the same logic works via row-level locking (no code change needed).
- The frontend polls lists every 10 s (no websockets, per scope).
- Capacity check: a request is invisible to a collector if `estimated_weight_kg >
  max_capacity_kg` (when capacity is set).
