"""Vercel Python function entrypoint for the FastAPI application."""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1] / "recycling-pickup-exchange" / "backend"
sys.path.insert(0, str(backend_dir))

from app.main import app
from starlette.types import Receive, Scope, Send


class StripApiPrefix:
	"""Make Vercel's /api/* function path match FastAPI's routes."""

	def __init__(self, application):
		self.application = application

	async def __call__(self, scope: Scope, receive: Receive, send: Send):
		if scope["type"] == "http" and scope["path"].startswith("/api"):
			scope = dict(scope)
			scope["path"] = scope["path"][4:] or "/"
			scope["raw_path"] = scope["raw_path"][4:] or b"/"
		await self.application(scope, receive, send)

app = StripApiPrefix(app)