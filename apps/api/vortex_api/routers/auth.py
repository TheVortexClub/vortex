import re
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    clear_session_cookie,
    current_user,
    get_session,
    hash_password,
    needs_rehash,
    set_session_cookie,
    verify_password,
)
from ..errors import VortexError
from ..models_db import User

router = APIRouter(prefix="/api/auth", tags=["Auth"])

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL.match(v):
            raise ValueError("E-mail inválido")
        return v


class Registration(Credentials):
    password: str = Field(min_length=8, max_length=256)
    name: str = Field("", max_length=100)


def user_out(user: User) -> dict[str, Any]:
    return {"id": user.id, "email": user.email, "name": user.name or user.email.split("@")[0]}


@router.get("/me", summary="Current user and auth mode")
async def me(request: Request, user: User = Depends(current_user)) -> dict[str, Any]:
    settings = request.app.state.settings
    return {
        "user": user_out(user),
        "local_mode": settings.local_mode,
        "allow_registration": settings.allow_registration,
    }


@router.get("/config", summary="Auth mode, for the login page (no login required)")
async def auth_config(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    return {"local_mode": settings.local_mode, "allow_registration": settings.allow_registration}


@router.post("/register", status_code=201, summary="Create an account")
async def register(
    body: Registration,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    settings = request.app.state.settings
    if settings.local_mode:
        raise VortexError(400, "Contas não são usadas no modo local", code="local_mode")
    if not settings.allow_registration:
        raise VortexError(403, "Cadastro desativado neste servidor", code="registration_closed")
    if await session.scalar(select(User).where(User.email == body.email)):
        raise VortexError(409, "Este e-mail já está cadastrado", code="email_taken")
    user = User(
        email=body.email, name=body.name.strip(), password_hash=hash_password(body.password)
    )
    session.add(user)
    await session.commit()
    token, exp = set_session_cookie(response, request, user.id)
    return {"user": user_out(user), "access_token": token, "expires_at": exp}


@router.post("/login", summary="Log in with e-mail and password")
async def login(
    body: Credentials,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await session.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(user.password_hash, body.password):
        raise VortexError(401, "E-mail ou senha inválidos", code="invalid_credentials")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
        await session.commit()
    token, exp = set_session_cookie(response, request, user.id)
    return {"user": user_out(user), "access_token": token, "expires_at": exp}


@router.post("/logout", status_code=204, summary="Log out")
async def logout(response: Response) -> Response:
    clear_session_cookie(response)
    response.status_code = 204
    return response
