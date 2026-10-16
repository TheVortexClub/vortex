"""Vortex's own from-scratch GPT (the `vortex` package + train.py checkpoints), run in-process.

Requires PyTorch (`pip install -e "apps/api[native]"`) and a trained model (`python train.py`).
"""

import asyncio
import importlib
import importlib.util
import sys
import threading
import time
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from ..errors import BackendError
from ..registry import BackendSpec
from .base import Backend
from .mock import _approx_tokens, _text_of

_END = object()

EngineFactory = Callable[[], Any]


def to_history(messages: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """OpenAI messages → the engine's [(role, text)] with roles 'user' / 'bot'.

    The character-level model was trained on user/bot turns only, so system prompts are dropped.
    """
    roles = {"user": "user", "assistant": "bot"}
    history = []
    for m in messages:
        role = roles.get(m.get("role"))
        text = _text_of(m.get("content")).strip()
        if role and text:
            history.append((role, text[:1000]))
    return history[-20:]


class NativeBackend(Backend):
    def __init__(self, spec: BackendSpec, engine_factory: EngineFactory | None = None) -> None:
        self.name = spec.name
        self.spec = spec
        self._factory = engine_factory or self._load_engine
        self._engine: Any = None
        self._load_lock = asyncio.Lock()
        self._gen_lock = threading.Lock()  # one generation at a time, like server.py

    def _checkpoint_files(self) -> list[Path]:
        ckpt = Path(self.spec.checkpoint_dir)
        return [ckpt / "vortex.pt", ckpt / "tokenizer.json"]

    def _load_engine(self) -> Any:
        missing = [str(p) for p in self._checkpoint_files() if not p.exists()]
        if missing:
            raise BackendError(
                f"Native Vortex model not trained yet (missing {', '.join(missing)}). "
                "Run `python train.py` in the repository root.",
                status_code=503,
            )
        if self.spec.path and self.spec.path not in sys.path:
            sys.path.insert(0, self.spec.path)
        try:
            engine_mod = importlib.import_module("vortex.engine")
        except ImportError as e:
            raise BackendError(
                f"Cannot import the native Vortex engine ({e}). "
                'Install PyTorch: pip install -e "apps/api[native]"',
                status_code=503,
            ) from e
        return engine_mod.Vortex(self.spec.checkpoint_dir, device=self.spec.device or None)

    async def _get_engine(self) -> Any:
        async with self._load_lock:
            if self._engine is None:
                self._engine = await asyncio.to_thread(self._factory)
        return self._engine

    def _gen_kwargs(self, payload: dict[str, Any]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if payload.get("max_tokens"):
            kwargs["max_new_tokens"] = int(payload["max_tokens"])
        for key in ("temperature", "top_p"):
            if payload.get(key) is not None:
                kwargs[key] = float(payload[key])
        return kwargs

    async def stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        history = to_history(payload.get("messages", []))
        if not history or history[-1][0] != "user":
            raise BackendError("The conversation must end with a user message", status_code=400)
        engine = await self._get_engine()
        kwargs = self._gen_kwargs(payload)

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Any] = asyncio.Queue()
        stop = threading.Event()

        def worker() -> None:
            try:
                with self._gen_lock:
                    for piece in engine.stream(history, **kwargs):
                        if stop.is_set():
                            break
                        loop.call_soon_threadsafe(queue.put_nowait, piece)
            except Exception as e:  # surfaced to the client as a backend error
                loop.call_soon_threadsafe(queue.put_nowait, e)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, _END)

        created = int(time.time())

        def chunk(delta: dict[str, Any], finish: str | None = None) -> dict[str, Any]:
            return {
                "id": "native",
                "object": "chat.completion.chunk",
                "created": created,
                "model": payload["model"],
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }

        loop.run_in_executor(None, worker)
        pieces = 0
        try:
            yield chunk({"role": "assistant", "content": ""})
            while (item := await queue.get()) is not _END:
                if isinstance(item, Exception):
                    raise BackendError(f"Native Vortex model failed: {item}")
                pieces += 1
                yield chunk({"content": item})
            yield chunk({}, "stop")
            if (payload.get("stream_options") or {}).get("include_usage"):
                prompt = " ".join(text for _, text in history)
                p = _approx_tokens(prompt)
                yield {
                    **chunk({}),
                    "choices": [],
                    "usage": {
                        "prompt_tokens": p,
                        "completion_tokens": pieces,
                        "total_tokens": p + pieces,
                    },
                }
        finally:
            stop.set()  # stops the generation thread if the client went away or cancelled

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        parts: list[str] = []
        async for c in self.stream_chat({**payload, "stream_options": None}):
            parts.append(c["choices"][0]["delta"].get("content") or "")
        text = "".join(parts).strip()
        prompt = " ".join(text for _, text in to_history(payload.get("messages", [])))
        p, n = _approx_tokens(prompt), max(1, len(text))
        return {
            "id": "native",
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
            "usage": {"prompt_tokens": p, "completion_tokens": n, "total_tokens": p + n},
        }

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise BackendError("The native Vortex model does not provide embeddings", status_code=400)

    async def health(self) -> dict[str, Any]:
        if self._engine is not None:
            return {"ok": True, "detail": "loaded"}
        missing = [p.name for p in self._checkpoint_files() if not p.exists()]
        if missing:
            return {"ok": False, "detail": "not trained yet: run `python train.py`"}
        if importlib.util.find_spec("torch") is None:
            return {"ok": False, "detail": 'PyTorch missing: pip install -e "apps/api[native]"'}
        return {"ok": True, "detail": "trained checkpoint found (loads on first request)"}
