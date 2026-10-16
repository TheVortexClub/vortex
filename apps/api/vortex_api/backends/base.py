from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class Backend(ABC):
    """A model server. Payloads and responses use the OpenAI wire format."""

    name: str

    @abstractmethod
    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed `chat.completion.chunk` objects."""

    @abstractmethod
    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Return {"ok": bool, "detail": str, ...}. Must not raise."""

    async def aclose(self) -> None:  # noqa: B027 - optional hook
        pass
