import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models_db import UsageEvent

log = logging.getLogger(__name__)

PLAN = {"name": "Livre", "credits": "Sem uso de créditos"}


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
    user_id: str | None = None


def _rnd(v: float | None) -> float | None:
    return round(float(v), 1) if v is not None else None


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

    async def summary(self, user_id: str | None = None) -> dict:
        """Totals for one user, or the whole server when user_id is None."""
        stmt = select(
            func.count(UsageEvent.id),
            func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
            func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
            func.avg(UsageEvent.latency_ms),
            func.avg(UsageEvent.ttft_ms),
            func.avg(UsageEvent.tokens_per_sec),
        )
        if user_id:
            stmt = stmt.where(UsageEvent.user_id == user_id)
        async with self._sessions() as session:
            count, prompt, completion, latency, ttft, tps = (await session.execute(stmt)).one()
        return {
            "requests": count,
            "prompt_tokens": int(prompt),
            "completion_tokens": int(completion),
            "total_tokens": int(prompt) + int(completion),
            "avg_latency_ms": _rnd(latency),
            "avg_ttft_ms": _rnd(ttft),
            "avg_tokens_per_sec": _rnd(tps),
            "plan": PLAN,
        }

    async def history(self, user_id: str | None, days: int) -> dict:
        """Per-day series (oldest first, every day present) and a per-model breakdown."""
        since = datetime.now(UTC) - timedelta(days=days - 1)
        since = since.replace(hour=0, minute=0, second=0, microsecond=0)
        day = func.date(UsageEvent.created_at)
        tokens = func.coalesce(UsageEvent.prompt_tokens, 0) + func.coalesce(
            UsageEvent.completion_tokens, 0
        )
        where = [UsageEvent.created_at >= since]
        if user_id:
            where.append(UsageEvent.user_id == user_id)

        per_day = (
            select(day, func.count(UsageEvent.id), func.sum(tokens)).where(*where).group_by(day)
        )
        per_model = (
            select(
                UsageEvent.model,
                func.count(UsageEvent.id),
                func.sum(tokens),
                func.avg(UsageEvent.latency_ms),
                func.avg(UsageEvent.tokens_per_sec),
            )
            .where(*where)
            .group_by(UsageEvent.model)
            .order_by(func.count(UsageEvent.id).desc())
        )
        async with self._sessions() as session:
            day_rows = {str(d): (n, t) for d, n, t in (await session.execute(per_day)).all()}
            model_rows = (await session.execute(per_model)).all()

        series = []
        for i in range(days):
            d = (since + timedelta(days=i)).date().isoformat()
            n, t = day_rows.get(d, (0, 0))
            series.append({"date": d, "requests": n, "tokens": int(t or 0)})
        return {
            "days": series,
            "models": [
                {
                    "model": m,
                    "requests": n,
                    "tokens": int(t or 0),
                    "avg_latency_ms": _rnd(lat),
                    "avg_tokens_per_sec": _rnd(tps),
                }
                for m, n, t, lat, tps in model_rows
            ],
        }
