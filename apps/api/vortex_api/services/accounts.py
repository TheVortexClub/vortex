"""Account-level operations shared by the user's own settings and the admin page."""

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import LOCAL_EMAIL
from ..models_db import (
    Conversation,
    File,
    FileChunk,
    Job,
    Memory,
    Message,
    Project,
    UsageEvent,
    User,
    UserSettings,
)


async def delete_conversations(session: AsyncSession, user_id: str) -> int:
    conv_ids = select(Conversation.id).where(Conversation.user_id == user_id)
    await session.execute(
        update(File).where(File.conversation_id.in_(conv_ids)).values(conversation_id=None)
    )
    await session.execute(delete(Message).where(Message.conversation_id.in_(conv_ids)))
    result = await session.execute(delete(Conversation).where(Conversation.user_id == user_id))
    return result.rowcount or 0


async def delete_user_data(session: AsyncSession, user_id: str, files_root=None) -> None:
    """Remove the user and everything they own. Usage stats are kept, anonymized."""
    files = (await session.scalars(select(File).where(File.user_id == user_id))).all()
    await session.execute(delete(FileChunk).where(FileChunk.file_id.in_([f.id for f in files])))
    await session.execute(delete(File).where(File.user_id == user_id))
    if files_root is not None:
        for f in files:
            (files_root / f.path).unlink(missing_ok=True)
    await session.execute(delete(Memory).where(Memory.user_id == user_id))
    await session.execute(delete(Job).where(Job.user_id == user_id))
    await delete_conversations(session, user_id)
    await session.execute(delete(Project).where(Project.user_id == user_id))
    await session.execute(delete(UserSettings).where(UserSettings.user_id == user_id))
    await session.execute(
        update(UsageEvent).where(UsageEvent.user_id == user_id).values(user_id=None)
    )
    await session.execute(delete(User).where(User.id == user_id))


async def account_users_count(session: AsyncSession) -> int:
    """Real accounts (the passwordless local-mode user doesn't count)."""
    return await session.scalar(select(func.count(User.id)).where(User.email != LOCAL_EMAIL)) or 0


async def admins_count(session: AsyncSession, exclude: str | None = None) -> int:
    stmt = select(func.count(User.id)).where(User.is_admin.is_(True), User.email != LOCAL_EMAIL)
    if exclude:
        stmt = stmt.where(User.id != exclude)
    return await session.scalar(stmt) or 0
