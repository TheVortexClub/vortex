"""Long-term memory: view, add, edit, delete, and turn off."""

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user, get_session
from ..errors import VortexError
from ..models_db import Memory, User, utcnow
from ..services.memory import MAX_MEMORY_CHARS
from ..services.workspace import user_settings
from .conversations import iso

router = APIRouter(prefix="/api/memory", tags=["Memory"])


class MemoryIn(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_MEMORY_CHARS)


def memory_out(m: Memory) -> dict[str, Any]:
    return {
        "id": m.id,
        "content": m.content,
        "source": m.source,
        "conversation_id": m.conversation_id,
        "created_at": iso(m.created_at),
        "updated_at": iso(m.updated_at),
    }


async def owned_memory(session: AsyncSession, user: User, memory_id: str) -> Memory:
    m = await session.get(Memory, memory_id)
    if m is None or m.user_id != user.id:
        raise VortexError(404, "Memória não encontrada", code="memory_not_found")
    return m


@router.get("", summary="What the Vortex remembers about you")
async def list_memories(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    memories = (
        await session.scalars(
            select(Memory).where(Memory.user_id == user.id).order_by(Memory.updated_at.desc())
        )
    ).all()
    prefs = await user_settings(session, user.id)
    return {"enabled": prefs.memory_enabled, "data": [memory_out(m) for m in memories]}


@router.post("", status_code=201, summary="Add a memory")
async def add_memory(
    body: MemoryIn, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    m = Memory(user_id=user.id, content=body.content.strip(), source="manual")
    session.add(m)
    await session.commit()
    return memory_out(m)


@router.patch("/{memory_id}", summary="Edit a memory")
async def edit_memory(
    memory_id: str,
    body: MemoryIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    m = await owned_memory(session, user, memory_id)
    m.content = body.content.strip()
    m.updated_at = utcnow()
    await session.commit()
    return memory_out(m)


@router.delete("/{memory_id}", status_code=204, summary="Forget one memory")
async def delete_memory(
    memory_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await session.delete(await owned_memory(session, user, memory_id))
    await session.commit()
    return Response(status_code=204)


@router.delete("", summary="Forget everything")
async def clear_memories(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, int]:
    result = await session.execute(delete(Memory).where(Memory.user_id == user.id))
    await session.commit()
    return {"deleted": result.rowcount or 0}
