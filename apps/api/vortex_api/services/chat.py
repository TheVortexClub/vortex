"""Chat completion logic shared by the /v1 routes: payload rewriting, streaming, cancellation."""

import asyncio
import json
import secrets
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from ..errors import BackendError, error_body
from ..registry import ModelSpec
from ..schemas import ChatCompletionRequest
from .usage import UsageRecord

OnDone = Callable[[UsageRecord], Awaitable[None]]


def new_id(prefix: str) -> str:
    return f"{prefix}-vx{secrets.token_hex(12)}"


def inject_system_prompt(prompt: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Put the model's identity prompt first, merged with the client's system message if any."""
    msgs = list(messages)
    first = msgs[0] if msgs else None
    if first and first.get("role") == "system" and isinstance(first.get("content"), str):
        msgs[0] = {**first, "content": f"{prompt}\n\n{first['content']}"}
    else:
        msgs.insert(0, {"role": "system", "content": prompt})
    return msgs


def build_chat_payload(spec: ModelSpec, req: ChatCompletionRequest) -> dict[str, Any]:
    payload = req.model_dump(exclude_none=True)
    payload["model"] = spec.upstream_model

    # Local servers understand max_tokens; newer OpenAI clients send max_completion_tokens.
    if "max_completion_tokens" in payload:
        payload.setdefault("max_tokens", payload.pop("max_completion_tokens"))
    for key, value in spec.defaults.items():
        payload.setdefault(key, value)

    messages = [
        {**m, "role": "system"} if m["role"] == "developer" else m for m in payload["messages"]
    ]
    if spec.system_prompt:
        messages = inject_system_prompt(spec.system_prompt, messages)
    payload["messages"] = messages

    if payload.get("stream"):
        # Always ask upstream for usage so we can record it; it's stripped if the client didn't ask.
        payload["stream_options"] = {"include_usage": True}
    else:
        payload.pop("stream_options", None)
    return payload


class GenerationRegistry:
    """Active streaming generations, so a client can stop one by id."""

    def __init__(self) -> None:
        self._active: dict[str, asyncio.Event] = {}

    def start(self, completion_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._active[completion_id] = event
        return event

    def cancel(self, completion_id: str) -> bool:
        event = self._active.get(completion_id)
        if event is None:
            return False
        event.set()
        return True

    def finish(self, completion_id: str) -> None:
        self._active.pop(completion_id, None)

    def __contains__(self, completion_id: str) -> bool:
        return completion_id in self._active


def sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _prepend(
    first: dict[str, Any] | None, stream: AsyncIterator[dict[str, Any]]
) -> AsyncIterator[dict[str, Any]]:
    try:
        if first is not None:
            yield first
        async for chunk in stream:
            yield chunk
    finally:
        await stream.aclose()  # closes the upstream HTTP stream, which stops generation


def _has_output(choices: list[dict[str, Any]]) -> bool:
    return any(
        (c.get("delta") or {}).get("content") or (c.get("delta") or {}).get("tool_calls")
        for c in choices
    )


def _throughput(
    completion_tokens: int | None, ttft: float | None, started: float, ended: float
) -> float | None:
    if not completion_tokens or ttft is None:
        return None
    generation_time = ended - started - ttft
    return completion_tokens / generation_time if generation_time > 0 else None


async def stream_completion(
    *,
    first: dict[str, Any] | None,
    stream: AsyncIterator[dict[str, Any]],
    spec: ModelSpec,
    completion_id: str,
    cancel: asyncio.Event,
    include_usage: bool,
    started: float,
    on_done: OnDone,
) -> AsyncIterator[str]:
    """Re-emit upstream chunks as Vortex SSE events, honoring stop requests."""
    ttft: float | None = None
    output_chunks = 0
    usage: dict[str, Any] | None = None
    status = "ok"
    created = int(time.time())

    chunks = _prepend(first, stream)
    try:
        async for chunk in chunks:
            if cancel.is_set():
                status = "cancelled"
                break
            chunk["id"] = completion_id
            chunk["model"] = spec.id
            created = chunk.get("created", created)
            if chunk.get("usage"):
                usage = chunk["usage"]
            choices = chunk.get("choices") or []
            if not choices:  # usage-only chunk
                if include_usage:
                    yield sse(chunk)
                continue
            if not include_usage:
                chunk.pop("usage", None)
            if _has_output(choices):
                output_chunks += 1
                if ttft is None:
                    ttft = time.perf_counter() - started
            yield sse(chunk)
    except BackendError as e:
        status = "error"
        yield sse(error_body(e.status_code, e.message, e.code))
    finally:
        await chunks.aclose()

    if status == "cancelled":
        yield sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": spec.id,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
        )
    yield "data: [DONE]\n\n"

    ended = time.perf_counter()
    completion_tokens = (usage or {}).get("completion_tokens") or output_chunks or None
    await on_done(
        UsageRecord(
            endpoint="chat.completions",
            model=spec.id,
            status=status,
            latency_ms=(ended - started) * 1000,
            prompt_tokens=(usage or {}).get("prompt_tokens"),
            completion_tokens=completion_tokens,
            ttft_ms=ttft * 1000 if ttft is not None else None,
            tokens_per_sec=_throughput(completion_tokens, ttft, started, ended),
        )
    )


def usage_from_response(
    spec: ModelSpec, response: dict[str, Any], started: float, endpoint: str
) -> UsageRecord:
    ended = time.perf_counter()
    usage = response.get("usage") or {}
    completion_tokens = usage.get("completion_tokens")
    elapsed = ended - started
    return UsageRecord(
        endpoint=endpoint,
        model=spec.id,
        status="ok",
        latency_ms=elapsed * 1000,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=completion_tokens,
        tokens_per_sec=(completion_tokens / elapsed) if completion_tokens and elapsed > 0 else None,
    )
