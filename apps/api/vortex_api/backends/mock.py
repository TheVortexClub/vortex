"""Offline simulator backend for tests, CI and UI development (VORTEX_MOCK_BACKEND=true)."""

import asyncio
import hashlib
import math
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from .base import Backend


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class MockBackend(Backend):
    def __init__(self, name: str = "mock", delay: float = 0.0) -> None:
        self.name = name
        self.delay = delay

    def _reply(self, payload: dict[str, Any]) -> str:
        user_turns = [m for m in payload.get("messages", []) if m.get("role") == "user"]
        last = _text_of(user_turns[-1].get("content")) if user_turns else ""
        return f"Olá! Eu sou o Vortex (modo simulado). Você disse: {last}"

    def _usage(self, payload: dict[str, Any], completion: str) -> dict[str, int]:
        prompt = " ".join(_text_of(m.get("content")) for m in payload.get("messages", []))
        p, c = _approx_tokens(prompt), _approx_tokens(completion)
        return {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = self._reply(payload)
        return {
            "id": "mock",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": payload["model"],
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": self._usage(payload, text),
        }

    async def stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        text = self._reply(payload)
        created = int(time.time())

        def chunk(delta: dict[str, Any], finish: str | None = None) -> dict[str, Any]:
            return {
                "id": "mock",
                "object": "chat.completion.chunk",
                "created": created,
                "model": payload["model"],
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }

        yield chunk({"role": "assistant", "content": ""})
        for piece in re.findall(r"\S+\s*", text):
            if self.delay:
                await asyncio.sleep(self.delay)
            yield chunk({"content": piece})
        yield chunk({}, "stop")
        if (payload.get("stream_options") or {}).get("include_usage"):
            yield {
                "id": "mock",
                "object": "chat.completion.chunk",
                "created": created,
                "model": payload["model"],
                "choices": [],
                "usage": self._usage(payload, text),
            }

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        inputs = payload["input"]
        if isinstance(inputs, str) or (inputs and isinstance(inputs[0], int)):
            inputs = [inputs]
        dims = payload.get("dimensions") or 16
        data = []
        for i, item in enumerate(inputs):
            seed = hashlib.sha256(str(item).encode()).digest()
            vec = [(seed[j % len(seed)] / 255.0) - 0.5 for j in range(dims)]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            data.append({"object": "embedding", "index": i, "embedding": [v / norm for v in vec]})
        tokens = sum(_approx_tokens(str(x)) for x in inputs)
        return {
            "object": "list",
            "data": data,
            "model": payload["model"],
            "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
        }

    async def health(self) -> dict[str, Any]:
        return {"ok": True, "detail": "mock backend (simulated responses)"}
