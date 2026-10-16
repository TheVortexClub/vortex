"""Long-term memory: facts the user asks the Vortex to remember, recalled in later chats."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models_db import Memory
from .rag import tokens

# "lembre que eu moro no Rio", "memorize: prefiro respostas curtas", "remember that ..."
_TRIGGER = re.compile(
    r"^\s*(?:por favor,?\s*|please,?\s*)?"
    r"(?:lembre(?:-se)?|lembra|memorize|guarde|anote|grave|remember)"
    r"(?:\s+(?:de\s+)?(?:que|isso|isto|that))?\s*[:,-]?\s*(?P<fact>.+)$",
    re.IGNORECASE | re.DOTALL,
)

MAX_MEMORY_CHARS = 500
MAX_IN_PROMPT = 15


def memory_request(text: str) -> str | None:
    """The fact to remember when the message asks for it explicitly, else None."""
    match = _TRIGGER.match(text)
    if not match:
        return None
    fact = match.group("fact").strip().rstrip(".!")
    if len(fact) < 3:
        return None
    return fact[:MAX_MEMORY_CHARS]


async def memories_context(session: AsyncSession, user_id: str, query: str) -> str | None:
    memories = (
        await session.scalars(
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.updated_at.desc())
            .limit(200)
        )
    ).all()
    if not memories:
        return None
    if len(memories) > MAX_IN_PROMPT:
        query_tokens = set(tokens(query))
        # most related first; recency (list order) breaks ties
        memories = sorted(memories, key=lambda m: -len(query_tokens & set(tokens(m.content))))[
            :MAX_IN_PROMPT
        ]
    facts = "\n".join(f"- {m.content}" for m in memories)
    return (
        "O que você lembra sobre o usuário (memória de longo prazo que ele pediu para você "
        f"guardar; use só quando for relevante):\n{facts}"
    )
