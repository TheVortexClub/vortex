"""Your settings: model parameters, custom instructions, tools, and your data."""

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user, get_session
from ..errors import VortexError
from ..models_db import Conversation, File, Memory, Message, Project, User
from ..services.accounts import delete_conversations
from ..services.workspace import TOOL_IDS, tool_catalog, user_settings
from .conversations import conversation_out, message_out
from .projects import project_out

router = APIRouter(prefix="/api", tags=["Settings"])


class SettingsUpdate(BaseModel):
    """Only the fields you send are changed. Send null to go back to the server default."""

    default_model: str | None = None
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=16, le=32768)
    custom_instructions: str | None = Field(None, max_length=4000)
    tools: dict[str, bool] | None = None
    memory_enabled: bool | None = None


def settings_out(row) -> dict[str, Any]:
    return {
        "default_model": row.default_model,
        "temperature": row.temperature,
        "max_tokens": row.max_tokens,
        "custom_instructions": row.custom_instructions or "",
        "memory_enabled": row.memory_enabled,
        "tools": tool_catalog(row.tools or {}),
    }


@router.get("/settings", summary="Your settings")
async def get_settings_(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    return settings_out(await user_settings(session, user.id))


@router.patch("/settings", summary="Change your settings")
async def update_settings(
    body: SettingsUpdate,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = await user_settings(session, user.id)
    sent = body.model_fields_set
    if "default_model" in sent and body.default_model:
        request.app.state.registry.resolve(body.default_model, "chat")
    if body.tools is not None:
        unknown = set(body.tools) - TOOL_IDS
        if unknown:
            raise VortexError(400, f"Ferramentas desconhecidas: {sorted(unknown)}", code="bad_tool")
        row.tools = {**(row.tools or {}), **body.tools}
    for field in ("default_model", "temperature", "max_tokens"):
        if field in sent:
            setattr(row, field, getattr(body, field))
    if body.custom_instructions is not None:
        row.custom_instructions = body.custom_instructions.strip()
    if body.memory_enabled is not None:
        row.memory_enabled = body.memory_enabled
    session.add(row)
    await session.commit()
    return settings_out(row)


@router.get("/settings/export", summary="Download all your data (JSON)")
async def export_data(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> Response:
    convs = (
        await session.scalars(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.created_at)
        )
    ).all()
    messages = (
        await session.scalars(
            select(Message)
            .where(Message.conversation_id.in_([c.id for c in convs]))
            .order_by(Message.created_at, Message.id)
        )
    ).all()
    by_conv: dict[str, list] = {}
    for m in messages:
        by_conv.setdefault(m.conversation_id, []).append(message_out(m))
    projects = (await session.scalars(select(Project).where(Project.user_id == user.id))).all()
    memories = (await session.scalars(select(Memory).where(Memory.user_id == user.id))).all()
    files = (await session.scalars(select(File).where(File.user_id == user.id))).all()
    data = {
        "exported_at": datetime.now(UTC).isoformat(),
        "user": {"email": user.email, "name": user.name},
        "settings": settings_out(await user_settings(session, user.id)),
        "projects": [project_out(p) for p in projects],
        "memories": [
            {"content": m.content, "created_at": m.created_at.isoformat()} for m in memories
        ],
        "files": [
            {"name": f.name, "kind": f.kind, "size": f.size, "project_id": f.project_id}
            for f in files
        ],
        "conversations": [
            {**conversation_out(c), "messages": by_conv.get(c.id, [])} for c in convs
        ],
    }
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="vortex-meus-dados.json"'},
    )


@router.delete("/conversations", summary="Delete all your conversations")
async def delete_all_conversations(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, int]:
    deleted = await delete_conversations(session, user.id)
    await session.commit()
    return {"deleted": deleted}
