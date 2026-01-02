"""Rate limiting and security middleware."""

import hashlib
import os
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from vote_api.connections import get_redis
from vote_api.services.fingerprint import get_client_ip


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for vote endpoints."""

    def __init__(self, app):
        super().__init__(app)
        self.votes_per_minute = int(os.getenv("VOTE_RL_PER_MIN", "10"))
        self.requests_per_second = int(os.getenv("API_RL_PER_SEC", "20"))

    def _identity(self, request: Request) -> str:
        """Get rate limit identity from request."""
        ip = get_client_ip(request)
        return hashlib.sha256(ip.encode()).hexdigest()[:16]

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        path = request.url.path

        # Apply stricter limits to vote endpoints
        if path.startswith("/api/v1/vote") and request.method == "POST":
            ident = self._identity(request)
            now = int(time.time())
            vote_key = f"vote:rl:min:{ident}:{now // 60}"

            try:
                redis_client = get_redis()
                count = redis_client.incr(vote_key)
                redis_client.expire(vote_key, 120)

                if count > self.votes_per_minute:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Vote rate limit exceeded"},
                    )
            except Exception:
                pass  # Fail open for rate limiting

        # Apply general rate limiting to all API endpoints
        if path.startswith("/api/"):
            ident = self._identity(request)
            now = int(time.time())
            sec_key = f"vote:rl:sec:{ident}:{now}"

            try:
                redis_client = get_redis()
                count = redis_client.incr(sec_key)
                redis_client.expire(sec_key, 2)

                if count > self.requests_per_second:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded"},
                    )
            except Exception:
                pass

        return await call_next(request)
