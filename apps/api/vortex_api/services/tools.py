"""Live availability of each tool.

A tool is usable when the roadmap delivered it, the user enabled it and the server has it set up.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from .documents import ocr_available
from .images import comfy_status
from .jobs import tool_client
from .sandbox import availability as sandbox_availability
from .workspace import DELIVERED_STEP, TOOLS

CACHE_SECONDS = 20


async def _searxng(state) -> tuple[bool, str]:
    try:
        async with tool_client(state, timeout=3) as client:
            r = await client.get(f"{state.settings.searxng_url.rstrip('/')}/healthz")
            r.raise_for_status()
        return True, "pronto"
    except httpx.HTTPError:
        return False, "O SearXNG (pesquisa local) não está rodando no servidor."


async def service_status(state) -> dict[str, tuple[bool, str]]:
    """Probe the services once and cache the answer for a few seconds."""
    cached = getattr(state, "tool_status_cache", None)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    async def comfy() -> tuple[bool, str]:
        async with tool_client(state, timeout=3) as client:
            return await comfy_status(client, state.settings.comfyui_url)

    web, image, sandbox = await asyncio.gather(
        _searxng(state), comfy(), sandbox_availability(state.settings.sandbox_image)
    )
    status = {
        "web_search": web,
        "image_generation": image,
        "code": sandbox,
        "data": sandbox,
        "file_analysis": (True, "pronto"),
        "ocr": (True, "pronto")
        if ocr_available()
        else (False, "O OCR não está instalado no servidor."),
    }
    state.tool_status_cache = (time.monotonic(), status)
    return status


async def tool_statuses(state, enabled: dict[str, bool]) -> list[dict[str, Any]]:
    services = await service_status(state)
    out = []
    for t in TOOLS:
        delivered = t["step"] <= DELIVERED_STEP
        ready, reason = services.get(t["id"], (delivered, "pronto"))
        if not delivered:
            ready, reason = False, f"Chega na etapa {t['step']} do roadmap."
        out.append(
            {
                **t,
                "enabled": enabled.get(t["id"], True),
                "available": delivered and ready,
                "reason": reason,
            }
        )
    return out


async def usable(state, enabled: dict[str, bool], tool_id: str) -> tuple[bool, str]:
    """Can this user use this tool right now? (enabled AND available)"""
    for t in await tool_statuses(state, enabled):
        if t["id"] == tool_id:
            if not t["enabled"]:
                return False, f"A ferramenta {t['label']} está desligada nas suas configurações."
            return t["available"], t["reason"]
    return False, "Ferramenta desconhecida."
