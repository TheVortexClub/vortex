"""Per-IP sliding-window rate limiter (in memory, single process)."""

import time
from collections import defaultdict, deque

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .errors import error_body

EXEMPT_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, limit_per_minute: int, window: float = 60.0) -> None:
        self.app = app
        self.limit = limit_per_minute
        self.window = window
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if (
            scope["type"] != "http"
            or self.limit <= 0
            or scope.get("method") == "OPTIONS"
            or path.startswith(EXEMPT_PREFIXES)
        ):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        ip = client[0] if client else "unknown"
        now = time.monotonic()
        hits = self.hits[ip]
        while hits and now - hits[0] >= self.window:
            hits.popleft()

        if len(hits) >= self.limit:
            retry_after = int(self.window - (now - hits[0])) + 1
            response = JSONResponse(
                error_body(429, "Rate limit exceeded. Try again shortly.", "rate_limit_exceeded"),
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return

        hits.append(now)
        if len(self.hits) > 10_000:
            self._prune(now)
        await self.app(scope, receive, send)

    def _prune(self, now: float) -> None:
        for ip in [ip for ip, h in self.hits.items() if not h or now - h[-1] >= self.window]:
            del self.hits[ip]
