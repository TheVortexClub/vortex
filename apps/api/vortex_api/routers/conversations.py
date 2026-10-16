"""Chat history: conversations and messages, scoped to the logged-in user."""

import json
import re
import time
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user, get_session
from ..errors import BackendError, VortexError
from ..models_db import DEFAULT_TITLE, Conversation, Message, User, utcnow
from ..schemas import ChatCompletionRequest
from ..services.chat import _prepend, build_chat_payload, new_id
from ..services.modes import Mode, system_instructions
from ..services.usage import UsageRecord

router = APIRouter(prefix="/api", tags=["Conversations"])


# ---------------------------------------------------------------- schemas / output


class ConversationCreate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    model: str | None = None
    mode: Mode = "conversar"


class ConversationUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    pinned: bool | None = None
    model: str | None = None
    mode: Mode | None = None


class ChatRequest(BaseModel):
    content: str | None = Field(None, max_length=32_000)
    model: str | None = None
    mode: Mode | None = None
    think: bool = False
    regenerate: bool = False
    edit_message_id: str | None = None


class BranchRequest(BaseModel):
    message_id: str


class FeedbackRequest(BaseModel):
    feedback: Literal[-1, 0, 1]


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:  # SQLite returns naive datetimes; they are stored in UTC
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def conversation_out(c: Conversation) -> dict[str, Any]:
    return {
        "id": c.id,
        "title": c.title,
        "model": c.model,
        "mode": c.mode,
        "pinned": c.pinned,
        "created_at": iso(c.created_at),
        "updated_at": iso(c.updated_at),
    }


def message_out(m: Message) -> dict[str, Any]:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "role": m.role,
        "content": m.content,
        "reasoning": m.reasoning,
        "model": m.model,
        "status": m.status,
        "feedback": m.feedback,
        "created_at": iso(m.created_at),
    }


def make_title(text: str) -> str:
    line = re.sub(r"\s+", " ", text.strip().splitlines()[0] if text.strip() else "").strip()
    return (line[:60].rstrip() + "…") if len(line) > 60 else (line or DEFAULT_TITLE)


def sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------- helpers


async def owned_conversation(session: AsyncSession, user: User, conv_id: str) -> Conversation:
    conv = await session.get(Conversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise VortexError(404, "Conversa não encontrada", code="conversation_not_found")
    return conv


async def conversation_messages(session: AsyncSession, conv_id: str) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at, Message.id)
    )
    return list((await session.scalars(stmt)).all())


def _check_model(request: Request, model: str | None) -> None:
    if model:
        request.app.state.registry.resolve(model, "chat")


# ---------------------------------------------------------------- CRUD


@router.get("/conversations", summary="List conversations (pinned first); q searches text")
async def list_conversations(
    q: str | None = Query(None, max_length=200),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    stmt = select(Conversation).where(Conversation.user_id == user.id)
    if q and q.strip():
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        in_messages = select(Message.conversation_id).where(
            Message.content.ilike(like, escape="\\")
        )
        stmt = stmt.where(
            or_(Conversation.title.ilike(like, escape="\\"), Conversation.id.in_(in_messages))
        )
    stmt = stmt.order_by(Conversation.pinned.desc(), Conversation.updated_at.desc()).limit(limit)
    return {"data": [conversation_out(c) for c in (await session.scalars(stmt)).all()]}


@router.post("/conversations", status_code=201, summary="Create a conversation")
async def create_conversation(
    body: ConversationCreate,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _check_model(request, body.model)
    conv = Conversation(
        user_id=user.id, title=body.title or DEFAULT_TITLE, model=body.model, mode=body.mode
    )
    session.add(conv)
    await session.commit()
    return conversation_out(conv)


@router.get("/conversations/{conv_id}", summary="A conversation with its messages")
async def get_conversation(
    conv_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    conv = await owned_conversation(session, user, conv_id)
    messages = await conversation_messages(session, conv.id)
    return {**conversation_out(conv), "messages": [message_out(m) for m in messages]}


@router.patch("/conversations/{conv_id}", summary="Rename, pin, or change model/mode")
async def update_conversation(
    conv_id: str,
    body: ConversationUpdate,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    conv = await owned_conversation(session, user, conv_id)
    _check_model(request, body.model)
    for field in ("title", "pinned", "model", "mode"):
        value = getattr(body, field)
        if value is not None:
            setattr(conv, field, value.strip() if isinstance(value, str) else value)
    await session.commit()
    return conversation_out(conv)


@router.delete("/conversations/{conv_id}", status_code=204, summary="Delete a conversation")
async def delete_conversation(
    conv_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    conv = await owned_conversation(session, user, conv_id)
    await session.execute(delete(Message).where(Message.conversation_id == conv.id))
    await session.delete(conv)
    await session.commit()
    return Response(status_code=204)


@router.post(
    "/conversations/{conv_id}/branch",
    status_code=201,
    summary="New conversation copying messages up to (and including) message_id",
)
async def branch_conversation(
    conv_id: str,
    body: BranchRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    conv = await owned_conversation(session, user, conv_id)
    messages = await conversation_messages(session, conv.id)
    cut = next((i for i, m in enumerate(messages) if m.id == body.message_id), None)
    if cut is None:
        raise VortexError(404, "Mensagem não encontrada", code="message_not_found")
    branch = Conversation(
        user_id=user.id, title=f"{conv.title} (ramificação)"[:200], model=conv.model, mode=conv.mode
    )
    session.add(branch)
    await session.flush()
    for m in messages[: cut + 1]:
        session.add(
            Message(
                conversation_id=branch.id,
                role=m.role,
                content=m.content,
                reasoning=m.reasoning,
                model=m.model,
                status=m.status,
                created_at=m.created_at,
            )
        )
    await session.commit()
    return conversation_out(branch)


@router.get("/conversations/{conv_id}/export", summary="Export as Markdown")
async def export_conversation(
    conv_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> PlainTextResponse:
    conv = await owned_conversation(session, user, conv_id)
    lines = [f"# {conv.title}", ""]
    for m in await conversation_messages(session, conv.id):
        who = "Você" if m.role == "user" else "Vortex"
        lines += [f"**{who}:**", "", m.content, ""]
    slug = re.sub(r"[^a-z0-9]+", "-", conv.title.lower()).strip("-")[:50] or "conversa"
    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{slug}.md"'},
    )


@router.patch("/messages/{message_id}", summary="Like / dislike a message")
async def message_feedback(
    message_id: str,
    body: FeedbackRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    msg = await session.get(Message, message_id)
    if msg is None:
        raise VortexError(404, "Mensagem não encontrada", code="message_not_found")
    await owned_conversation(session, user, msg.conversation_id)
    msg.feedback = body.feedback or None
    await session.commit()
    return message_out(msg)


# ---------------------------------------------------------------- chat (SSE)


@router.post(
    "/conversations/{conv_id}/chat",
    summary="Send, regenerate or edit, streaming the answer (SSE)",
    description=(
        "Server-sent events: `meta` (ids), `delta` ({content} or {reasoning}), "
        "`error`, and `done` (the saved assistant message). "
        "Stop with POST /v1/chat/completions/{completion_id}/cancel."
    ),
)
async def chat(
    conv_id: str,
    body: ChatRequest,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    state = request.app.state
    conv = await owned_conversation(session, user, conv_id)
    messages = await conversation_messages(session, conv.id)

    _check_model(request, body.model)
    if body.model:
        conv.model = body.model
    if body.mode:
        conv.mode = body.mode
    spec = state.registry.resolve(conv.model, "chat")

    user_msg: Message | None = None
    if body.regenerate:
        while messages and messages[-1].role == "assistant":
            await session.delete(messages.pop())
        if not messages:
            raise VortexError(400, "Nada para regenerar", code="nothing_to_regenerate")
    elif body.edit_message_id:
        idx = next(
            (
                i
                for i, m in enumerate(messages)
                if m.id == body.edit_message_id and m.role == "user"
            ),
            None,
        )
        if idx is None:
            raise VortexError(404, "Mensagem não encontrada", code="message_not_found")
        if not (body.content and body.content.strip()):
            raise VortexError(400, "A mensagem não pode ficar vazia", code="empty_message")
        for m in messages[idx + 1 :]:
            await session.delete(m)
        messages = messages[: idx + 1]
        user_msg = messages[idx]
        user_msg.content = body.content.strip()
    else:
        if not (body.content and body.content.strip()):
            raise VortexError(400, "A mensagem não pode ficar vazia", code="empty_message")
        user_msg = Message(conversation_id=conv.id, role="user", content=body.content.strip())
        session.add(user_msg)
        if conv.title == DEFAULT_TITLE and not any(m.role == "user" for m in messages):
            conv.title = make_title(body.content)
        messages.append(user_msg)
    conv.updated_at = utcnow()
    await session.commit()

    history: list[dict[str, Any]] = [
        {"role": m.role, "content": m.content}
        for m in messages
        if m.role in ("user", "assistant") and m.content
    ]
    if instructions := system_instructions(conv.mode, body.think):
        history.insert(0, {"role": "system", "content": instructions})
    payload = build_chat_payload(spec, ChatCompletionRequest(messages=history, stream=True))

    # Start upstream before answering, so a dead backend is a proper HTTP error.
    stream = state.gateway.backend_for(spec).stream_chat(payload)
    try:
        first = await anext(stream)
    except StopAsyncIteration:
        first = None

    completion_id = new_id("chatcmpl")
    cancel = state.generations.start(completion_id)
    meta = {
        "conversation": conversation_out(conv),
        "user_message": message_out(user_msg) if user_msg else None,
        "completion_id": completion_id,
        "model": spec.id,
    }

    async def events():
        content: list[str] = []
        reasoning: list[str] = []
        usage: dict[str, Any] = {}
        status = "ok"
        started = time.perf_counter()
        ttft: float | None = None
        chunks = _prepend(first, stream)
        yield sse_event("meta", meta)
        try:
            async for chunk in chunks:
                if cancel.is_set():
                    status = "cancelled"
                    break
                usage = chunk.get("usage") or usage
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    if r := delta.get("reasoning_content") or delta.get("reasoning"):
                        reasoning.append(r)
                        yield sse_event("delta", {"reasoning": r})
                    if c := delta.get("content"):
                        if ttft is None:
                            ttft = time.perf_counter() - started
                        content.append(c)
                        yield sse_event("delta", {"content": c})
        except BackendError as e:
            status = "error"
            yield sse_event("error", {"message": e.message})
        finally:
            await chunks.aclose()
            state.generations.finish(completion_id)

        saved = None
        if content or reasoning:
            async with state.sessions() as s:
                msg = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content="".join(content),
                    reasoning="".join(reasoning) or None,
                    model=spec.id,
                    status=status,
                )
                s.add(msg)
                if c := await s.get(Conversation, conv_id):
                    c.updated_at = utcnow()
                await s.commit()
                saved = message_out(msg)

        elapsed = time.perf_counter() - started
        tokens = usage.get("completion_tokens") or len(content) or None
        gen_time = elapsed - (ttft or 0)
        await state.usage.record(
            UsageRecord(
                endpoint="api.chat",
                model=spec.id,
                status=status,
                latency_ms=elapsed * 1000,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=tokens,
                ttft_ms=ttft * 1000 if ttft is not None else None,
                tokens_per_sec=(tokens / gen_time) if tokens and ttft and gen_time > 0 else None,
            )
        )
        yield sse_event("done", {"message": saved, "status": status, "usage": usage or None})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
