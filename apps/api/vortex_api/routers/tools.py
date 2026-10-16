"""Tools: status, isolated code execution, image generation and background jobs."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user, get_session
from ..errors import VortexError
from ..models_db import Conversation, File, Job, User
from ..services.files import absolute_path
from ..services.jobs import save_generated, schedule_job
from ..services.sandbox import run_python
from ..services.tools import tool_statuses, usable
from ..services.workspace import user_settings
from .conversations import iso
from .files import file_out

router = APIRouter(prefix="/api", tags=["Tools"])


class CodeRun(BaseModel):
    code: str = Field(min_length=1, max_length=20_000)
    language: Literal["python"] = "python"
    file_ids: list[str] = Field(default_factory=list, max_length=5)
    conversation_id: str | None = None


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)
    negative: str = Field(
        "borrado, distorcido, baixa qualidade, texto, marca d'água", max_length=500
    )
    width: int = Field(512, ge=256, le=1024)
    height: int = Field(512, ge=256, le=1024)
    steps: int = Field(20, ge=1, le=50)
    seed: int | None = Field(None, ge=0, le=2**31 - 1)
    conversation_id: str | None = None

    @field_validator("width", "height")
    @classmethod
    def multiple_of_64(cls, v: int) -> int:
        return v - v % 64


def job_out(j: Job, files: list[File] | None = None) -> dict[str, Any]:
    return {
        "id": j.id,
        "kind": j.kind,
        "prompt": j.prompt,
        "params": j.params,
        "status": j.status,
        "progress": j.progress,
        "error": j.error,
        "result_file_ids": j.result_file_ids or [],
        "files": [file_out(f) for f in files or []],
        "conversation_id": j.conversation_id,
        "created_at": iso(j.created_at),
        "finished_at": iso(j.finished_at) if j.finished_at else None,
    }


async def _require(request: Request, session: AsyncSession, user: User, tool_id: str) -> None:
    prefs = await user_settings(session, user.id)
    ok, reason = await usable(request.app.state, prefs.tools or {}, tool_id)
    if not ok:
        raise VortexError(409, reason, code="tool_unavailable")


async def _owned_conversation_id(session, user, conv_id: str | None) -> str | None:
    if conv_id:
        conv = await session.get(Conversation, conv_id)
        if conv is None or conv.user_id != user.id:
            raise VortexError(404, "Conversa não encontrada", code="conversation_not_found")
    return conv_id


@router.get("/tools", summary="Tools with live availability on this server")
async def list_tools(
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    prefs = await user_settings(session, user.id)
    return {"data": await tool_statuses(request.app.state, prefs.tools or {})}


@router.post("/tools/code/run", summary="Run Python in the isolated sandbox")
async def run_code(
    body: CodeRun,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    state = request.app.state
    await _require(request, session, user, "code")
    conv_id = await _owned_conversation_id(session, user, body.conversation_id)

    files: list[File] = []
    for file_id in body.file_ids:
        f = await session.get(File, file_id)
        if f is None or f.user_id != user.id:
            raise VortexError(404, "Arquivo não encontrado", code="file_not_found")
        files.append(f)
    if not body.file_ids and conv_id:
        # No explicit choice: the conversation's own uploads are available at /data.
        files = list(
            (
                await session.scalars(
                    select(File).where(
                        File.conversation_id == conv_id,
                        File.origin == "upload",
                        File.status == "ready",
                    )
                )
            ).all()
        )[:10]

    mounted: list[tuple[str, object]] = []
    used_names: set[str] = set()
    for f in files:
        name = f.name
        while name in used_names:
            name = f"_{name}"
        used_names.add(name)
        mounted.append((name, absolute_path(state, f)))

    settings = state.settings
    async with state.sandbox_slots:
        result = await run_python(
            body.code,
            mounted,
            image=settings.sandbox_image,
            time_limit=settings.sandbox_timeout,
            memory=settings.sandbox_memory,
        )

    images = []
    for name, data in result.images:
        f = save_generated(state, user.id, name, data, "code", conv_id)
        session.add(f)
        images.append(f)
    await session.commit()
    return {
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration": result.duration,
        "timed_out": result.timed_out,
        "images": [file_out(f) for f in images],
    }


@router.post("/images", status_code=202, summary="Generate an image (runs in the background)")
async def create_image(
    body: ImageRequest,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _require(request, session, user, "image_generation")
    conv_id = await _owned_conversation_id(session, user, body.conversation_id)
    job = Job(
        user_id=user.id,
        kind="image",
        prompt=body.prompt.strip(),
        params=body.model_dump(exclude={"prompt", "conversation_id"}),
        status="queued",
        progress=0.0,
        result_file_ids=[],
        conversation_id=conv_id,
    )
    session.add(job)
    await session.commit()
    schedule_job(request.app.state, job.id)
    return job_out(job)


async def _job_files(session: AsyncSession, job: Job) -> list[File]:
    if not job.result_file_ids:
        return []
    files = (await session.scalars(select(File).where(File.id.in_(job.result_file_ids)))).all()
    order = {fid: i for i, fid in enumerate(job.result_file_ids)}
    return sorted(files, key=lambda f: order.get(f.id, 0))


@router.get("/jobs", summary="Your image/video jobs, newest first")
async def list_jobs(
    kind: Literal["image", "video"] | None = Query(None),
    limit: int = Query(30, ge=1, le=200),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    stmt = select(Job).where(Job.user_id == user.id)
    if kind:
        stmt = stmt.where(Job.kind == kind)
    jobs = (await session.scalars(stmt.order_by(Job.created_at.desc()).limit(limit))).all()
    return {"data": [job_out(j, await _job_files(session, j)) for j in jobs]}


@router.get("/jobs/{job_id}", summary="One job (poll this for progress)")
async def get_job(
    job_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    job = await session.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise VortexError(404, "Tarefa não encontrada", code="job_not_found")
    return job_out(job, await _job_files(session, job))
