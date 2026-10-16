from typing import Any

from fastapi import APIRouter, Depends, Request

from .. import __version__
from ..auth import current_user

router = APIRouter(tags=["System"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/api/health", summary="API and model backend status")
async def api_health(request: Request) -> dict[str, Any]:
    """`status` follows the default chat model's backend; optional backends only show in detail."""
    registry = request.app.state.registry
    backends = await request.app.state.gateway.health()
    default_backend = registry.resolve(None, "chat").backend
    return {
        "status": "ok" if backends[default_backend]["ok"] else "degraded",
        "default_model": registry.defaults["chat"],
        "version": __version__,
        "local_mode": request.app.state.settings.local_mode,
        "backends": backends,
    }


@router.get("/api/models", summary="Models with display metadata for the UI")
async def api_models(request: Request) -> dict[str, Any]:
    registry = request.app.state.registry
    return {
        "data": [
            {
                "id": m.id,
                "kind": m.kind,
                "display_name": m.display_name,
                "version": m.version,
                "badge": m.badge,
                "description": m.description,
                "aliases": list(m.aliases),
                "capabilities": list(m.capabilities),
                "context_window": m.context_window,
                "dimensions": m.dimensions,
                "default": registry.defaults.get(m.kind) == m.id,
            }
            for m in registry.list()
        ]
    }


@router.get(
    "/api/usage",
    tags=["Usage"],
    summary="Token, latency and throughput totals",
    dependencies=[Depends(current_user)],
)
async def api_usage(request: Request) -> dict[str, Any]:
    return await request.app.state.usage.summary()
