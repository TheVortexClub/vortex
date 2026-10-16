"""Server administration: who uses this server and whether new people can sign up."""

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import __version__
from ..auth import LOCAL_EMAIL, get_session, require_admin
from ..errors import VortexError
from ..models_db import Conversation, Message, User
from ..services.accounts import admins_count, delete_user_data
from ..services.files import files_root
from ..services.workspace import registration_open, set_server_setting
from .conversations import iso

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class ServerUpdate(BaseModel):
    allow_registration: bool


class UserUpdate(BaseModel):
    is_admin: bool


@router.get("/server", summary="Server overview")
async def server_info(
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    users = await session.scalar(select(func.count(User.id)).where(User.email != LOCAL_EMAIL))
    return {
        "version": __version__,
        "local_mode": request.app.state.settings.local_mode,
        "allow_registration": await registration_open(request, session),
        "users": users or 0,
        "conversations": await session.scalar(select(func.count(Conversation.id))) or 0,
        "messages": await session.scalar(select(func.count(Message.id))) or 0,
    }


@router.patch("/server", summary="Open or close sign-ups")
async def update_server(
    body: ServerUpdate,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await set_server_setting(
        session, "allow_registration", "true" if body.allow_registration else "false"
    )
    await session.commit()
    return {"allow_registration": await registration_open(request, session)}


@router.get("/users", summary="Accounts on this server")
async def list_users(
    _: User = Depends(require_admin), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    stats = (
        select(
            Conversation.user_id,
            func.count(Conversation.id).label("n"),
            func.max(Conversation.updated_at).label("last"),
        )
        .group_by(Conversation.user_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(User, stats.c.n, stats.c.last)
            .outerjoin(stats, stats.c.user_id == User.id)
            .where(User.email != LOCAL_EMAIL)
            .order_by(User.created_at)
        )
    ).all()
    return {
        "data": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name or u.email.split("@")[0],
                "is_admin": bool(u.is_admin),
                "created_at": iso(u.created_at),
                "conversations": n or 0,
                "last_activity": iso(last) if last else None,
            }
            for u, n, last in rows
        ]
    }


async def _target(session: AsyncSession, user_id: str) -> User:
    user = await session.get(User, user_id)
    if user is None or user.email == LOCAL_EMAIL:
        raise VortexError(404, "Usuário não encontrado", code="user_not_found")
    return user


@router.patch("/users/{user_id}", summary="Grant or remove admin")
async def update_user(
    user_id: str,
    body: UserUpdate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await _target(session, user_id)
    if not body.is_admin and await admins_count(session, exclude=user.id) == 0:
        raise VortexError(
            409, "O servidor precisa de pelo menos um administrador", code="last_admin"
        )
    user.is_admin = body.is_admin
    await session.commit()
    return {"id": user.id, "is_admin": user.is_admin}


@router.delete("/users/{user_id}", status_code=204, summary="Delete an account and its data")
async def delete_user(
    user_id: str,
    request: Request,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if user_id == admin.id:
        raise VortexError(
            400, "Use Configurações > Dados para apagar a sua própria conta", code="self"
        )
    await _target(session, user_id)
    await delete_user_data(session, user_id, files_root(request.app.state))
    await session.commit()
    return Response(status_code=204)
