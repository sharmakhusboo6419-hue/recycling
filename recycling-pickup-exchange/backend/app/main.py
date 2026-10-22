"""FastAPI application entrypoint.

Run with: uvicorn app.main:app --reload  (from the backend/ directory)
"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.caching import ETagMiddleware
from app.database import init_db
from app.routers import collector, household, profiles, stats

load_dotenv()

init_db()

app = FastAPI(
    title="Recycling Pickup Exchange",
    description="Connects households with recyclable-waste collectors. Team Nexora — Tech Fusion 2026.",
    version="1.0.0",
)

# CORS: allow the Vite dev server (env-configurable, comma-separated list).
allowed_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:5174"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ETagMiddleware)


@app.middleware("http")
async def strip_vercel_api_prefix(request: Request, call_next):
    """Allow the Vercel service rewrite to preserve the public /api prefix."""
    if request.scope["path"].startswith("/api"):
        request.scope["path"] = request.scope["path"][4:] or "/"
        request.scope["raw_path"] = request.scope["raw_path"][4:] or b"/"
    return await call_next(request)

app.include_router(profiles.router)
app.include_router(household.router)
app.include_router(collector.router)
app.include_router(stats.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Consistent JSON error format for anything unhandled."""
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {exc}"})


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
