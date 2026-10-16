import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

DEFAULT_TITLE = "Nova conversa"


def new_uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC)


class UsageEvent(Base):
    """One model call: tokens, latency and throughput, for the usage dashboard."""

    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    endpoint: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[float] = mapped_column(Float)
    ttft_ms: Mapped[float | None] = mapped_column(Float)
    tokens_per_sec: Mapped[float | None] = mapped_column(Float)
    user_id: Mapped[str | None] = mapped_column(String(32), index=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    # None for the passwordless local-mode user
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), default=DEFAULT_TITLE)
    model: Mapped[str | None] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(32), default="conversar")
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    project_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text, default="")
    reasoning: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok | cancelled | error
    feedback: Mapped[int | None] = mapped_column(Integer)  # 1 like, -1 dislike
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Project(Base):
    """A workspace grouping conversations (and, later, files and agents) with shared context."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(16), default="blue")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserSettings(Base):
    """Per-user preferences; None means "use the server default"."""

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    default_model: Mapped[str | None] = mapped_column(String(128))
    temperature: Mapped[float | None] = mapped_column(Float)
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    custom_instructions: Mapped[str] = mapped_column(Text, default="")
    tools: Mapped[dict] = mapped_column(JSON, default=dict)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(8), default="pt-BR")


class ServerSetting(Base):
    """Settings the server admin changes at runtime (override .env defaults)."""

    __tablename__ = "server_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
