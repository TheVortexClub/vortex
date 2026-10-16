"""Request models for the OpenAI-compatible API. Unknown fields are passed through upstream."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: Literal["system", "developer", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None


class StreamOptions(BaseModel):
    include_usage: bool = False


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "model": "vortex-v0.2.1",
                    "messages": [{"role": "user", "content": "Olá, Vortex!"}],
                    "stream": False,
                }
            ]
        },
    )

    model: str | None = Field(None, description="Model id or alias. Defaults to Vortex v0.2.1.")
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    stream_options: StreamOptions | None = None
    temperature: float | None = Field(None, ge=0, le=2)
    top_p: float | None = Field(None, ge=0, le=1)
    max_tokens: int | None = Field(None, ge=1)
    max_completion_tokens: int | None = Field(None, ge=1)
    stop: str | list[str] | None = None
    seed: int | None = None
    presence_penalty: float | None = Field(None, ge=-2, le=2)
    frequency_penalty: float | None = Field(None, ge=-2, le=2)
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    response_format: dict[str, Any] | None = None
    user: str | None = None


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={"examples": [{"model": "vortex-embed", "input": "Olá, mundo"}]},
    )

    model: str | None = Field(None, description="Embedding model id. Defaults to vortex-embed.")
    input: str | list[str] | list[int] | list[list[int]]
    encoding_format: Literal["float", "base64"] | None = None
    dimensions: int | None = Field(None, ge=1)
    user: str | None = None
