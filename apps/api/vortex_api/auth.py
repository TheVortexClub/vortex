"""Accounts without API keys: argon2 passwords + short-lived JWT in an httpOnly cookie.

In local mode (single-user installs) every request runs as a built-in local user, no login.
"""

import logging
import secrets
import time
from collections.abc import AsyncIterator
from pathlib import Path

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .errors import VortexError
from .models_db import User

log = logging.getLogger(__name__)

COOKIE_NAME = "vortex_session"
LOCAL_EMAIL = "local@vortex.local"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def load_secret(settings: Settings) -> str:
    """Use VORTEX_SECRET_KEY, or generate one once and keep it in the data dir."""
    if settings.secret_key:
        return settings.secret_key
    path = Path(settings.data_dir) / ".secret_key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_urlsafe(48)
    path.write_text(secret, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    log.info("Generated a new session secret in %s", path)
    return secret


def issue_token(user_id: str, secret: str, hours: int) -> tuple[str, int]:
    exp = int(time.time()) + hours * 3600
    return jwt.encode({"sub": user_id, "exp": exp}, secret, algorithm="HS256"), exp


def decode_token(token: str, secret: str) -> dict | None:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["sub", "exp"]})
    except jwt.PyJWTError:
        return None


def set_session_cookie(response: Response, request: Request, user_id: str) -> tuple[str, int]:
    """Set the httpOnly session cookie; returns (token, exp) for Bearer-token clients."""
    settings: Settings = request.app.state.settings
    token, exp = issue_token(user_id, request.app.state.secret, settings.session_hours)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return token, exp


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessions() as session:
        yield session


async def _local_user(request: Request, session: AsyncSession) -> User:
    cached = getattr(request.app.state, "local_user_id", None)
    if cached and (user := await session.get(User, cached)):
        return user
    user = await session.scalar(select(User).where(User.email == LOCAL_EMAIL))
    if user is None:
        user = User(email=LOCAL_EMAIL, name="Você")
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:  # created by a concurrent request
            await session.rollback()
            user = await session.scalar(select(User).where(User.email == LOCAL_EMAIL))
    request.app.state.local_user_id = user.id
    return user


def _token_from(request: Request) -> str | None:
    if token := request.cookies.get(COOKIE_NAME):
        return token
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


async def current_user(
    request: Request, response: Response, session: AsyncSession = Depends(get_session)
) -> User:
    settings: Settings = request.app.state.settings
    if settings.local_mode:
        return await _local_user(request, session)

    token = _token_from(request)
    claims = decode_token(token, request.app.state.secret) if token else None
    user = await session.get(User, claims["sub"]) if claims else None
    if user is None:
        raise VortexError(401, "Faça login para continuar", code="unauthenticated")

    # Sliding session: renew the cookie once half of its lifetime has passed.
    if claims["exp"] - time.time() < settings.session_hours * 1800:
        set_session_cookie(response, request, user.id)
    return user
