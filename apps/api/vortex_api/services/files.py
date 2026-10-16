"""File storage, background processing (extract → chunk → embed) and chat context building."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models_db import Conversation, File, FileChunk
from .documents import extract, ocr_available
from .rag import Passage, chunk_pages, embed, format_context, rank, to_bytes

log = logging.getLogger(__name__)


def files_root(state) -> Path:
    return Path(state.settings.data_dir) / "files"


def absolute_path(state, f: File) -> Path:
    return files_root(state) / f.path


def remove_from_disk(state, f: File) -> None:
    try:
        absolute_path(state, f).unlink(missing_ok=True)
    except OSError as e:
        log.warning("Could not delete %s: %s", f.path, e)


async def delete_files(session: AsyncSession, state, files: list[File]) -> None:
    ids = [f.id for f in files]
    if not ids:
        return
    await session.execute(delete(FileChunk).where(FileChunk.file_id.in_(ids)))
    await session.execute(delete(File).where(File.id.in_(ids)))
    for f in files:
        remove_from_disk(state, f)


def schedule_processing(state, file_id: str) -> None:
    task = asyncio.get_running_loop().create_task(process_file(state, file_id))
    state.background.add(task)
    task.add_done_callback(state.background.discard)


async def process_file(state, file_id: str) -> None:
    async with state.processing_slots:  # at most a couple of files at once on a CPU server
        async with state.sessions() as s:
            f = await s.get(File, file_id)
            if f is None:
                return
            path, kind = absolute_path(state, f), f.kind
        try:
            extracted = await asyncio.to_thread(extract, path, kind)
            chunks = chunk_pages(extracted.pages)
            vectors = await embed(state, [t for _, t in chunks]) if chunks else None
            async with state.sessions() as s:
                f = await s.get(File, file_id)
                if f is None:  # deleted while processing
                    return
                for i, (page, text) in enumerate(chunks):
                    s.add(
                        FileChunk(
                            file_id=file_id,
                            idx=i,
                            page=page,
                            text=text,
                            embedding=to_bytes(vectors[i]) if vectors else None,
                        )
                    )
                f.chars = len(extracted.text)
                f.pages = sum(1 for p, _ in extracted.pages if p is not None) or None
                f.ocr = extracted.ocr
                f.embedded = vectors is not None
                if chunks:
                    f.status = "ready"
                else:
                    f.status = "error"
                    f.error = (
                        "Não encontrei texto neste arquivo."
                        if kind != "image" or ocr_available()
                        else "OCR não está instalado no servidor, então não consigo ler imagens."
                    )
                await s.commit()
        except Exception as e:  # any parser failure becomes a visible file error
            log.warning("Processing %s failed: %s", file_id, e)
            async with state.sessions() as s:
                f = await s.get(File, file_id)
                if f is not None:
                    f.status = "error"
                    f.error = f"Não consegui ler o arquivo ({type(e).__name__})."
                    await s.commit()


async def build_context(
    session: AsyncSession,
    state,
    conv: Conversation,
    new_file_ids: list[str],
    query: str,
) -> tuple[str | None, list[dict[str, Any]]]:
    """File passages for this chat turn: the conversation's files plus its project's files."""
    budget = state.settings.rag_context_chars
    scope = [File.conversation_id == conv.id]
    if conv.project_id:
        scope.append(File.project_id == conv.project_id)
    files = (
        await session.scalars(
            select(File).where(File.user_id == conv.user_id, File.status == "ready", or_(*scope))
        )
    ).all()
    if not files:
        return None, []
    by_id = {f.id: f for f in files}
    rows = (
        await session.scalars(
            select(FileChunk)
            .where(FileChunk.file_id.in_(list(by_id)))
            .order_by(FileChunk.file_id, FileChunk.idx)
        )
    ).all()
    chunks_of: dict[str, list[FileChunk]] = {}
    for c in rows:
        chunks_of.setdefault(c.file_id, []).append(c)

    picked: list[FileChunk] = []
    used = 0

    def take(chunk: FileChunk) -> bool:
        nonlocal used
        if chunk in picked or used + len(chunk.text) > budget:
            return False
        picked.append(chunk)
        used += len(chunk.text)
        return True

    # 1. Files sent with this message come first: whole, or their beginning if too long.
    new = [i for i in new_file_ids if i in by_id]
    new_total = sum(len(c.text) for i in new for c in chunks_of.get(i, []))
    if new:
        limit = budget if new_total <= budget else budget // 2
        for i in new:
            for c in chunks_of.get(i, []):
                if used + len(c.text) > limit:
                    break
                take(c)

    # 2. Fill the rest with the passages most related to the question.
    if used < budget:
        candidates = [c for c in rows if c not in picked]
        if sum(len(c.text) for c in candidates) + used <= budget:
            for c in candidates:
                take(c)
        else:
            query_vector = None
            if all(by_id[c.file_id].embedded for c in candidates):
                vectors = await embed(state, [query])
                query_vector = vectors[0] if vectors else None
            ranked = rank(
                query,
                query_vector,
                [
                    (c.file_id, by_id[c.file_id].name, c.page, c.text, c.embedding)
                    for c in candidates
                ],
            )
            lookup = {(c.file_id, c.text): c for c in candidates}
            for p in ranked:
                if p.score <= 0 and query_vector is None and picked:
                    break
                take(lookup[(p.file_id, p.text)])
                if used >= budget * 0.95:
                    break

    if not picked:
        return None, []
    picked.sort(key=lambda c: (c.file_id, c.idx))
    passages = [Passage(c.file_id, by_id[c.file_id].name, c.page, c.text, 0) for c in picked]
    sources: list[dict[str, Any]] = []
    for c in picked:
        src = {"file_id": c.file_id, "name": by_id[c.file_id].name, "page": c.page}
        if src not in sources:
            sources.append(src)
    return format_context(passages), sources
