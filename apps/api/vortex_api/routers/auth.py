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
from ..services.accounts import account_users_count, admins_count, delete_user_data
from ..services.workspace import registration_open

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


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class AccountDeletion(BaseModel):
    password: str = Field(min_length=1, max_length=256)


def user_out(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "is_admin": bool(user.is_admin),
    }


def _no_accounts_in_local_mode(request: Request) -> None:
    if request.app.state.settings.local_mode:
        raise VortexError(400, "Contas não são usadas no modo local", code="local_mode")


@router.get("/me", summary="Current user and auth mode")
async def me(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return {
        "user": user_out(user),
        "local_mode": request.app.state.settings.local_mode,
        "allow_registration": await registration_open(request, session),
    }


@router.get("/config", summary="Auth mode, for the login page (no login required)")
async def auth_config(
    request: Request, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    return {
        "local_mode": request.app.state.settings.local_mode,
        "allow_registration": await registration_open(request, session),
    }


@router.post("/register", status_code=201, summary="Create an account")
async def register(
    body: Registration,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _no_accounts_in_local_mode(request)
    first_account = await account_users_count(session) == 0
    # The very first account can always be created: it becomes the server admin.
    if not first_account and not await registration_open(request, session):
        raise VortexError(403, "Cadastro desativado neste servidor", code="registration_closed")
    if await session.scalar(select(User).where(User.email == body.email)):
        raise VortexError(409, "Este e-mail já está cadastrado", code="email_taken")
    user = User(
        email=body.email,
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        is_admin=first_account or await admins_count(session) == 0,
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


@router.patch("/me", summary="Update your profile")
async def update_profile(
    body: ProfileUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user.name = body.name.strip()
    await session.commit()
    return {"user": user_out(user)}


@router.post("/password", status_code=204, summary="Change your password")
async def change_password(
    body: PasswordChange,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    _no_accounts_in_local_mode(request)
    if not verify_password(user.password_hash, body.current_password):
        raise VortexError(400, "A senha atual está incorreta", code="wrong_password")
    user.password_hash = hash_password(body.new_password)
    await session.commit()
    return Response(status_code=204)


@router.delete("/me", status_code=204, summary="Delete your account and all your data")
async def delete_account(
    body: AccountDeletion,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    _no_accounts_in_local_mode(request)
    if not verify_password(user.password_hash, body.password):
        raise VortexError(400, "Senha incorreta", code="wrong_password")
    others = await account_users_count(session) - 1
    if user.is_admin and others > 0 and await admins_count(session, exclude=user.id) == 0:
        raise VortexError(
            409,
            "Você é o único administrador. Torne outra pessoa administradora antes de sair.",
            code="last_admin",
        )
    await delete_user_data(session, user.id)
    await session.commit()
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response
