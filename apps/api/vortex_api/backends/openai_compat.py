"""Backend for any server speaking the OpenAI API: Ollama (/v1), llama.cpp server, vLLM."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..errors import BackendError
from ..registry import BackendSpec
from .base import Backend


class OpenAICompatBackend(Backend):
    def __init__(
        self,
        spec: BackendSpec,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.name = spec.name
        headers = {"Authorization": f"Bearer {spec.api_key}"} if spec.api_key else {}
        self._client = httpx.AsyncClient(
            base_url=spec.base_url.rstrip("/") + "/",
            headers=headers,
            timeout=httpx.Timeout(spec.timeout or timeout, connect=10.0),
            transport=transport,
        )

    def _unreachable(self, exc: Exception) -> BackendError:
        return BackendError(
            f"Model backend '{self.name}' is unreachable ({type(exc).__name__}). "
            "Is the model server running?",
            status_code=503,
        )

    def _upstream_error(self, status: int, body: str) -> BackendError:
        return BackendError(f"Model backend '{self.name}' returned {status}: {body[:500]}")

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(path, json=payload)
        except httpx.HTTPError as e:
            raise self._unreachable(e) from e
        if response.status_code >= 400:
            raise self._upstream_error(response.status_code, response.text)
        return response.json()

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post_json("chat/completions", payload)

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post_json("embeddings", payload)

    async def stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        try:
            async with self._client.stream("POST", "chat/completions", json=payload) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", "replace")
                    raise self._upstream_error(response.status_code, body)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue  # blank separators, ": keep-alive" comments, event: lines
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
        except httpx.HTTPError as e:
            raise self._unreachable(e) from e

    async def health(self) -> dict[str, Any]:
        try:
            response = await self._client.get("models", timeout=5.0)
            response.raise_for_status()
            models = [m.get("id") for m in response.json().get("data", [])]
            return {"ok": True, "detail": "reachable", "upstream_models": models}
        except (httpx.HTTPError, ValueError) as e:
            return {"ok": False, "detail": f"{type(e).__name__}: {e}"}

    async def aclose(self) -> None:
        await self._client.aclose()
