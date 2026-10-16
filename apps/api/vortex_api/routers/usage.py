"""Usage and performance: your tokens, latency and speed, plus the server's hardware."""

import asyncio
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request

from ..auth import current_user
from ..errors import VortexError
from ..models_db import User
from ..services.system_stats import hardware, ollama_loaded

router = APIRouter(prefix="/api", tags=["Usage"])


def _scope_user(user: User, scope: str) -> str | None:
    if scope == "server":
        if not user.is_admin:
            raise VortexError(
                403, "Apenas administradores veem o uso do servidor", code="admin_only"
            )
        return None
    return user.id


@router.get("/usage", summary="Token, latency and throughput totals")
async def usage(
    request: Request,
    scope: Literal["me", "server"] = "me",
    user: User = Depends(current_user),
) -> dict[str, Any]:
    return await request.app.state.usage.summary(_scope_user(user, scope))


@router.get("/usage/history", summary="Per-day and per-model usage")
async def usage_history(
    request: Request,
    days: int = Query(14, ge=1, le=90),
    scope: Literal["me", "server"] = "me",
    user: User = Depends(current_user),
) -> dict[str, Any]:
    return await request.app.state.usage.history(_scope_user(user, scope), days)


@router.get(
    "/system", summary="Server hardware and loaded models", dependencies=[Depends(current_user)]
)
async def system(request: Request) -> dict[str, Any]:
    registry = request.app.state.registry
    stats = await asyncio.to_thread(hardware)
    ollama = registry.backends.get("ollama")
    loaded = None
    if ollama and not request.app.state.settings.mock_backend:
        loaded = await ollama_loaded(ollama.base_url)
    return {**stats, "loaded_models": loaded}
