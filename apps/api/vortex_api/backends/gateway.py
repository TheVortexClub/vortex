import asyncio
from typing import Any

import httpx

from ..config import Settings
from ..registry import ModelSpec, Registry, RegistryError
from .base import Backend
from .mock import MockBackend
from .native import NativeBackend
from .openai_compat import OpenAICompatBackend

OPENAI_COMPAT_TYPES = {"openai_compat", "ollama", "llamacpp", "vllm"}


class ModelGateway:
    """Owns one client per backend in the registry and routes models to them."""

    def __init__(
        self,
        registry: Registry,
        settings: Settings,
        transports: dict[str, httpx.AsyncBaseTransport] | None = None,
    ) -> None:
        self.registry = registry
        self.backends: dict[str, Backend] = {}
        transports = transports or {}
        for name, spec in registry.backends.items():
            if settings.mock_backend or spec.type == "mock":
                self.backends[name] = MockBackend(name)
            elif spec.type in OPENAI_COMPAT_TYPES:
                self.backends[name] = OpenAICompatBackend(
                    spec, settings.request_timeout, transports.get(name)
                )
            elif spec.type == "native":
                self.backends[name] = NativeBackend(spec)
            else:
                raise RegistryError(f"backend '{name}': unsupported type '{spec.type}'")

    def backend_for(self, model: ModelSpec) -> Backend:
        return self.backends[model.backend]

    async def health(self) -> dict[str, dict[str, Any]]:
        names = sorted(self.registry.used_backends())
        results = await asyncio.gather(*(self.backends[n].health() for n in names))
        return dict(zip(names, results, strict=True))

    async def aclose(self) -> None:
        await asyncio.gather(*(b.aclose() for b in self.backends.values()))
