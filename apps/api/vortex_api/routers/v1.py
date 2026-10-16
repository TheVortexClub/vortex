"""OpenAI-compatible API: point any OpenAI SDK at http://<host>:8000/v1 (no key needed)."""

import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..auth import current_user
from ..errors import VortexError
from ..registry import ModelSpec
from ..schemas import ChatCompletionRequest, EmbeddingRequest
from ..services.chat import (
    build_chat_payload,
    new_id,
    stream_completion,
    usage_from_response,
)

# In local mode current_user is the built-in user; with accounts, a login is required.
router = APIRouter(
    prefix="/v1", tags=["OpenAI-compatible"], dependencies=[Depends(current_user)]
)


def _openai_model(spec: ModelSpec) -> dict[str, Any]:
    return {"id": spec.id, "object": "model", "created": spec.created, "owned_by": "vortex"}


@router.get("/models", summary="List models")
async def list_models(request: Request) -> dict[str, Any]:
    registry = request.app.state.registry
    return {"object": "list", "data": [_openai_model(m) for m in registry.list()]}


@router.get("/models/{model_id}", summary="Retrieve a model")
async def get_model(model_id: str, request: Request) -> dict[str, Any]:
    spec = request.app.state.registry.models.get(model_id)
    if spec is None:
        raise VortexError(404, f"The model '{model_id}' does not exist", code="model_not_found")
    return _openai_model(spec)


@router.post("/chat/completions", summary="Create a chat completion (SSE when stream=true)")
async def chat_completions(body: ChatCompletionRequest, request: Request):
    state = request.app.state
    spec = state.registry.resolve(body.model, "chat")
    backend = state.gateway.backend_for(spec)
    payload = build_chat_payload(spec, body)
    completion_id = new_id("chatcmpl")
    started = time.perf_counter()

    if not body.stream:
        result = await backend.chat(payload)
        result["id"] = completion_id
        result["model"] = spec.id
        await state.usage.record(usage_from_response(spec, result, started, "chat.completions"))
        return result

    # Pull the first chunk before answering, so an unreachable backend becomes a proper HTTP error.
    stream = backend.stream_chat(payload)
    try:
        first = await anext(stream)
    except StopAsyncIteration:
        first = None

    generations = state.generations
    cancel = generations.start(completion_id)

    async def events():
        try:
            async for event in stream_completion(
                first=first,
                stream=stream,
                spec=spec,
                completion_id=completion_id,
                cancel=cancel,
                include_usage=bool(body.stream_options and body.stream_options.include_usage),
                started=started,
                on_done=state.usage.record,
            ):
                yield event
        finally:
            generations.finish(completion_id)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Vortex-Completion-Id": completion_id,
        },
    )


@router.post(
    "/chat/completions/{completion_id}/cancel",
    summary="Stop a streaming completion (Vortex extension)",
)
async def cancel_completion(completion_id: str, request: Request) -> dict[str, Any]:
    if not request.app.state.generations.cancel(completion_id):
        raise VortexError(
            404, f"No active generation with id '{completion_id}'", code="generation_not_found"
        )
    return {"id": completion_id, "object": "chat.completion.cancellation", "cancelled": True}


@router.post("/embeddings", summary="Create embeddings")
async def embeddings(body: EmbeddingRequest, request: Request) -> dict[str, Any]:
    state = request.app.state
    spec = state.registry.resolve(body.model, "embedding")
    payload = body.model_dump(exclude_none=True)
    payload["model"] = spec.upstream_model
    started = time.perf_counter()
    result = await state.gateway.backend_for(spec).embeddings(payload)
    result["model"] = spec.id
    await state.usage.record(usage_from_response(spec, result, started, "embeddings"))
    return result
