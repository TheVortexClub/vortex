"""Vortex API entry point.

uvicorn vortex_api.main:create_app --factory --reload
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker

from . import (
    __version__,
    models_db,  # noqa: F401 - registers tables on Base.metadata
)
from .auth import load_secret
from .backends import ModelGateway
from .config import Settings, get_settings
from .db import Base, make_engine
from .errors import install_error_handlers
from .ratelimit import RateLimitMiddleware
from .registry import Registry
from .routers import admin, auth, conversations, files, memory, projects, system, usage, v1
from .routers import settings as settings_routes
from .services.chat import GenerationRegistry
from .services.usage import UsageRecorder

log = logging.getLogger("vortex")

DESCRIPTION = """
**Vortex v0.2.1** — Muito mais que um chatbot. Um universo de possibilidades.

Self-hosted and OpenAI-compatible. No API key needed: point any OpenAI client at
`http://localhost:8000/v1`. With accounts enabled (`VORTEX_LOCAL_MODE=false`), log in via
`/api/auth/login` and send the session cookie (or `Authorization: Bearer <token>`).
"""


def create_app(
    settings: Settings | None = None,
    *,
    transports: dict[str, httpx.AsyncBaseTransport] | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    registry = Registry.load(settings.registry_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings.database_url)
        if settings.db_auto_create:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        app.state.sessions = sessions
        app.state.usage = UsageRecorder(sessions)
        app.state.gateway = ModelGateway(registry, settings, transports)
        app.state.generations = GenerationRegistry()
        app.state.background = set()  # file processing tasks
        app.state.processing_slots = asyncio.Semaphore(2)
        log.info("Vortex API %s ready (%d models)", __version__, len(registry.models))
        try:
            yield
        finally:
            # Stop file processing and let it unwind before the database goes away.
            tasks = list(app.state.background)
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.wait(tasks, timeout=10)
            await app.state.gateway.aclose()
            await engine.dispose()

    app = FastAPI(
        title="Vortex API",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.registry = registry
    app.state.secret = load_secret(settings)

    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Vortex-Completion-Id"],
    )
    install_error_handlers(app)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(conversations.router)
    app.include_router(projects.router)
    app.include_router(files.router)
    app.include_router(memory.router)
    app.include_router(settings_routes.router)
    app.include_router(usage.router)
    app.include_router(admin.router)
    app.include_router(v1.router)
    return app
