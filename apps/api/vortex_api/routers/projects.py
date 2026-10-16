"""Projects: workspaces that group conversations and share instructions (context)."""

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user, get_session
from ..errors import VortexError
from ..models_db import Conversation, Project, User, utcnow
from .conversations import conversation_out, iso

router = APIRouter(prefix="/api/projects", tags=["Projects"])

Color = Literal["blue", "violet", "pink", "amber", "emerald", "cyan"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field("", max_length=2000)
    instructions: str = Field("", max_length=8000)
    color: Color = "blue"


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=2000)
    instructions: str | None = Field(None, max_length=8000)
    color: Color | None = None


def aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes (stored as UTC); make them comparable."""
    return dt.replace(tzinfo=UTC) if dt is not None and dt.tzinfo is None else dt


def project_out(p: Project, conversations: int = 0, last_activity=None) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "instructions": p.instructions,
        "color": p.color,
        "conversation_count": conversations,
        "created_at": iso(p.created_at),
        "updated_at": iso(p.updated_at),
        "last_activity": iso(last_activity or p.updated_at),
    }


async def owned_project(session: AsyncSession, user: User, project_id: str) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise VortexError(404, "Projeto não encontrado", code="project_not_found")
    return project


@router.get("", summary="Your projects, most recently active first")
async def list_projects(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    stats = (
        select(
            Conversation.project_id,
            func.count(Conversation.id).label("n"),
            func.max(Conversation.updated_at).label("last"),
        )
        .where(Conversation.user_id == user.id, Conversation.project_id.is_not(None))
        .group_by(Conversation.project_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(Project, stats.c.n, stats.c.last)
            .outerjoin(stats, stats.c.project_id == Project.id)
            .where(Project.user_id == user.id)
        )
    ).all()
    data = [
        project_out(p, n or 0, max(filter(None, [aware(last), aware(p.updated_at)])))
        for p, n, last in rows
    ]
    data.sort(key=lambda d: d["last_activity"], reverse=True)
    return {"data": data}


@router.post("", status_code=201, summary="Create a project")
async def create_project(
    body: ProjectCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    project = Project(
        user_id=user.id,
        name=body.name.strip(),
        description=body.description.strip(),
        instructions=body.instructions.strip(),
        color=body.color,
    )
    session.add(project)
    await session.commit()
    return project_out(project)


@router.get("/{project_id}", summary="A project with its conversations")
async def get_project(
    project_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    project = await owned_project(session, user, project_id)
    convs = (
        await session.scalars(
            select(Conversation)
            .where(Conversation.project_id == project.id, Conversation.user_id == user.id)
            .order_by(Conversation.pinned.desc(), Conversation.updated_at.desc())
        )
    ).all()
    last = max([aware(c.updated_at) for c in convs] + [aware(project.updated_at)])
    return {
        **project_out(project, len(convs), last),
        "conversations": [conversation_out(c) for c in convs],
    }


@router.patch("/{project_id}", summary="Update a project")
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    project = await owned_project(session, user, project_id)
    for field in ("name", "description", "instructions", "color"):
        value = getattr(body, field)
        if value is not None:
            setattr(project, field, value.strip() if isinstance(value, str) else value)
    project.updated_at = utcnow()
    await session.commit()
    return project_out(project)


@router.delete(
    "/{project_id}",
    status_code=204,
    summary="Delete a project (its conversations are kept, just moved out)",
)
async def delete_project(
    project_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    project = await owned_project(session, user, project_id)
    await session.execute(
        update(Conversation).where(Conversation.project_id == project.id).values(project_id=None)
    )
    await session.delete(project)
    await session.commit()
    return Response(status_code=204)
