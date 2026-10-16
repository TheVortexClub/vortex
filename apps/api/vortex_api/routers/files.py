"""Files: upload (PDF, DOCX, XLSX, CSV, text/code, images), read, move and delete."""

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user, get_session
from ..errors import VortexError
from ..models_db import Conversation, File, FileChunk, Project, User, new_uuid
from ..services.documents import UnsupportedFile, detect_kind
from ..services.files import delete_files, files_root, schedule_processing
from .conversations import iso

router = APIRouter(prefix="/api/files", tags=["Files"])


class FileUpdate(BaseModel):
    project_id: str | None = None  # "" removes it from its project


def file_out(f: File) -> dict[str, Any]:
    return {
        "id": f.id,
        "name": f.name,
        "kind": f.kind,
        "mime": f.mime,
        "size": f.size,
        "status": f.status,
        "error": f.error,
        "pages": f.pages,
        "chars": f.chars,
        "ocr": f.ocr,
        "embedded": f.embedded,
        "project_id": f.project_id,
        "conversation_id": f.conversation_id,
        "created_at": iso(f.created_at),
    }


def safe_name(name: str) -> str:
    name = Path(name.replace("\\", "/")).name
    name = re.sub(r"[\x00-\x1f<>:\"/\\|?*]", "_", name).strip(" .")
    return name[:200] or "arquivo"


async def owned_file(session: AsyncSession, user: User, file_id: str) -> File:
    f = await session.get(File, file_id)
    if f is None or f.user_id != user.id:
        raise VortexError(404, "Arquivo não encontrado", code="file_not_found")
    return f


async def _check_owner(session: AsyncSession, user: User, model, obj_id: str | None, what: str):
    if obj_id:
        obj = await session.get(model, obj_id)
        if obj is None or obj.user_id != user.id:
            raise VortexError(404, f"{what} não encontrado", code="not_found")


@router.post("", status_code=201, summary="Upload a file (processed in the background)")
async def upload(
    request: Request,
    file: UploadFile,
    project_id: str | None = Form(None),
    conversation_id: str | None = Form(None),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    state = request.app.state
    await _check_owner(session, user, Project, project_id, "Projeto")
    await _check_owner(session, user, Conversation, conversation_id, "Conversa")

    name = safe_name(file.filename or "arquivo")
    limit = state.settings.max_upload_mb * 1024 * 1024
    head = await file.read(16)
    try:
        kind, mime = detect_kind(name, head)
    except UnsupportedFile as e:
        raise VortexError(415, str(e), code="unsupported_file") from e

    file_id = new_uuid()
    rel = Path(user.id) / f"{file_id}{Path(name).suffix.lower()}"
    dest = files_root(state) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = len(head)
    try:
        with dest.open("wb") as out:
            out.write(head)
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise VortexError(
                        413,
                        f"Arquivo grande demais (limite de {state.settings.max_upload_mb} MB).",
                        code="file_too_large",
                    )
                out.write(chunk)
    except VortexError:
        dest.unlink(missing_ok=True)
        raise

    f = File(
        id=file_id,
        user_id=user.id,
        project_id=project_id or None,
        conversation_id=conversation_id or None,
        name=name,
        kind=kind,
        mime=mime,
        size=size,
        path=rel.as_posix(),
        status="processing",
        chars=0,
        ocr=False,
        embedded=False,
    )
    session.add(f)
    await session.commit()
    schedule_processing(state, f.id)
    return file_out(f)


@router.get("", summary="Your files (optionally of one project or conversation)")
async def list_files(
    project_id: str | None = Query(None),
    conversation_id: str | None = Query(None),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    stmt = select(File).where(File.user_id == user.id)
    if project_id:
        stmt = stmt.where(File.project_id == project_id)
    if conversation_id:
        stmt = stmt.where(File.conversation_id == conversation_id)
    files = (await session.scalars(stmt.order_by(File.created_at.desc()))).all()
    return {"data": [file_out(f) for f in files]}


@router.get("/{file_id}", summary="File details and a preview of its text")
async def get_file(
    file_id: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    f = await owned_file(session, user, file_id)
    first = await session.scalar(
        select(FileChunk.text).where(FileChunk.file_id == f.id).order_by(FileChunk.idx).limit(1)
    )
    return {**file_out(f), "preview": (first or "")[:1500]}


@router.get("/{file_id}/content", summary="Download the original file")
async def download(
    file_id: str,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    f = await owned_file(session, user, file_id)
    path = files_root(request.app.state) / f.path
    if not path.exists():
        raise VortexError(404, "O arquivo não está mais no servidor", code="file_missing")
    # Always as a download, never rendered inline (uploaded HTML/SVG must not run in the site).
    return FileResponse(
        path,
        media_type="application/octet-stream" if f.kind != "image" else f.mime,
        filename=f.name,
        content_disposition_type="attachment" if f.kind != "image" else "inline",
        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"},
    )


@router.patch("/{file_id}", summary="Move a file into or out of a project")
async def update_file(
    file_id: str,
    body: FileUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    f = await owned_file(session, user, file_id)
    if body.project_id is not None:
        await _check_owner(session, user, Project, body.project_id, "Projeto")
        f.project_id = body.project_id or None
    await session.commit()
    return file_out(f)


@router.delete("/{file_id}", status_code=204, summary="Delete a file")
async def delete_file(
    file_id: str,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    f = await owned_file(session, user, file_id)
    await delete_files(session, request.app.state, [f])
    await session.commit()
    return Response(status_code=204)
