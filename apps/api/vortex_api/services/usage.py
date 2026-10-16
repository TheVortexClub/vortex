import logging
from dataclasses import asdict, dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models_db import UsageEvent

log = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    endpoint: str
    model: str
    status: str
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    ttft_ms: float | None = None
    tokens_per_sec: float | None = None


class UsageRecorder:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(self, rec: UsageRecord) -> None:
        """Store one event. Failures are logged and never break the request."""
        try:
            async with self._sessions() as session:
                session.add(UsageEvent(**asdict(rec)))
                await session.commit()
        except SQLAlchemyError as e:
            log.warning("Could not record usage (run `alembic upgrade head`?): %s", e)

    async def summary(self) -> dict:
        stmt = select(
            func.count(UsageEvent.id),
            func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
            func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
            func.avg(UsageEvent.latency_ms),
            func.avg(UsageEvent.ttft_ms),
            func.avg(UsageEvent.tokens_per_sec),
        )
        async with self._sessions() as session:
            count, prompt, completion, latency, ttft, tps = (await session.execute(stmt)).one()

        def rnd(v: float | None) -> float | None:
            return round(v, 1) if v is not None else None

        return {
            "requests": count,
            "prompt_tokens": int(prompt),
            "completion_tokens": int(completion),
            "total_tokens": int(prompt) + int(completion),
            "avg_latency_ms": rnd(latency),
            "avg_ttft_ms": rnd(ttft),
            "avg_tokens_per_sec": rnd(tps),
            "plan": {"name": "Livre", "credits": "Sem uso de créditos"},
        }
