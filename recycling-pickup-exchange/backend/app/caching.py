"""Simple HTTP caching helpers.

- ETagMiddleware: attaches an ETag (hash of the JSON body) to safe (GET/HEAD)
  responses and returns 304 Not Modified when the client sends a matching
  If-None-Match header. This makes the frontend's 10-second polling cheap:
  unchanged data is transferred as an empty 304.
- Cache-Control: short-lived freshness for GET list endpoints so repeat
  navigation can reuse the response without hitting the server.
"""
import hashlib
import json

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

# Methods that can be cached/validated.
SAFE_METHODS = {"GET", "HEAD"}


class ETagMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        if request.method in SAFE_METHODS and response.status_code == 200:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            etag = 'W/"%s"' % hashlib.md5(body).hexdigest()
            if request.headers.get("if-none-match") == etag:
                # Unchanged — respond 304 with an empty body.
                not_modified = JSONResponse(content=None, status_code=304)
                not_modified.headers["ETag"] = etag
                not_modified.headers["Cache-Control"] = "no-cache"
                return not_modified

            response.headers["ETag"] = etag
            # Small freshness window + always revalidate afterwards.
            response.headers["Cache-Control"] = "public, max-age=5, must-revalidate"

            async def stream():
                yield body

            response.body_iterator = stream()
        return response


def json_bytes(content) -> bytes:
    """Helper kept for tests — serialises like the app does."""
    return json.dumps(content).encode()
