"""Background jobs for slow tools (image generation now, video in step 8)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

from ..models_db import File, Job, new_uuid, utcnow
from .files import files_root
from .images import ImageError, generate, txt2img_workflow

log = logging.getLogger(__name__)


def tool_client(state, timeout: float = 30.0) -> httpx.AsyncClient:
    """HTTP client for tool services (SearXNG, ComfyUI). Tests inject a fake transport."""
    return httpx.AsyncClient(transport=state.tool_transport, timeout=timeout)


def save_generated(
    state, user_id: str, name: str, data: bytes, origin: str, conversation_id=None
) -> File:
    """Store a generated image as one of the user's files (it then shows in chat and library)."""
    file_id = new_uuid()
    suffix = Path(name).suffix.lower() or ".png"
    rel = Path(user_id) / f"{file_id}{suffix}"
    dest = files_root(state) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return File(
        id=file_id,
        user_id=user_id,
        conversation_id=conversation_id,
        name=name,
        kind="image",
        mime="image/png" if suffix == ".png" else f"image/{suffix[1:]}",
        size=len(data),
        path=rel.as_posix(),
        status="ready",
        chars=0,
        ocr=False,
        embedded=False,
        origin=origin,
    )


def schedule_job(state, job_id: str) -> None:
    task = asyncio.get_running_loop().create_task(run_job(state, job_id))
    state.background.add(task)
    task.add_done_callback(state.background.discard)


async def _update(state, job_id: str, **fields) -> None:
    async with state.sessions() as s:
        job = await s.get(Job, job_id)
        if job is not None:
            for k, v in fields.items():
                setattr(job, k, v)
            await s.commit()


async def run_job(state, job_id: str) -> None:
    async with state.job_slots:  # one generation at a time: they use all the CPU/GPU
        async with state.sessions() as s:
            job = await s.get(Job, job_id)
            if job is None:
                return
            kind, prompt, params, user_id, conv_id = (
                job.kind,
                job.prompt,
                dict(job.params),
                job.user_id,
                job.conversation_id,
            )
        await _update(state, job_id, status="running", progress=0.02)
        try:
            if kind != "image":
                raise ImageError("Tipo de tarefa não suportado ainda.")
            workflow = txt2img_workflow(
                prompt,
                params.get("negative", ""),
                params["width"],
                params["height"],
                params["steps"],
                params.get("seed"),
                state.settings.image_checkpoint,
            )

            async def progress(value: float) -> None:
                await _update(state, job_id, progress=round(value, 3))

            async with tool_client(state, timeout=60) as client:
                images = await generate(client, state.settings.comfyui_url, workflow, progress)

            async with state.sessions() as s:
                ids = []
                for n, (_, data) in enumerate(images, start=1):
                    f = save_generated(
                        state, user_id, f"imagem-{job_id[:6]}-{n}.png", data, "image", conv_id
                    )
                    s.add(f)
                    ids.append(f.id)
                job = await s.get(Job, job_id)
                job.status, job.progress, job.result_file_ids, job.finished_at = (
                    "done",
                    1.0,
                    ids,
                    utcnow(),
                )
                await s.commit()
        except ImageError as e:
            await _update(state, job_id, status="error", error=str(e), finished_at=utcnow())
        except Exception as e:  # never leave a job stuck in "running"
            log.exception("Job %s failed", job_id)
            await _update(
                state,
                job_id,
                status="error",
                error=f"Falha inesperada ({type(e).__name__}).",
                finished_at=utcnow(),
            )
