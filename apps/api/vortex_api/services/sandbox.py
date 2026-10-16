"""Runs Python in an isolated Docker container. Code never runs directly on the server.

Limits: no network, read-only filesystem, no Linux capabilities, unprivileged user, CPU/memory/
process caps and a time limit. The chat's files are mounted read-only at /data; charts saved
to /out (or left open in matplotlib) come back as images.

Docker is called through subprocess in a worker thread (works with any asyncio loop on Windows).
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

MAX_OUTPUT = 20_000
MAX_IMAGES = 6
_availability: tuple[float, bool, str] | None = None


@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False
    images: list[tuple[str, bytes]] = field(default_factory=list)  # (name, png bytes)


def _run(args: list[str], *, stdin: bytes | None = None, timeout: float = 20):
    """(returncode, stdout, stderr, timed_out)"""
    try:
        r = subprocess.run(args, input=stdin, capture_output=True, timeout=timeout, check=False)
        return r.returncode, r.stdout, r.stderr, False
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout or b"", e.stderr or b"", True
    except OSError as e:
        return 127, b"", str(e).encode(), False


def _check(image: str) -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "Docker não está instalado no servidor."
    code, out, err, _ = _run(["docker", "image", "inspect", image, "--format", "{{.Id}}"])
    if code == 0:
        return True, "pronto"
    message = (out + err).decode(errors="replace").lower()
    if "cannot connect" in message or "daemon" in message or "pipe" in message:
        return False, "O Docker não está rodando no servidor."
    return False, f"Falta preparar o ambiente isolado (imagem {image})."


async def availability(image: str) -> tuple[bool, str]:
    """(ok, reason) — cached for 30 s."""
    global _availability
    now = time.monotonic()
    if _availability and now - _availability[0] < 30:
        return _availability[1], _availability[2]
    ok, reason = await asyncio.to_thread(_check, image)
    _availability = (now, ok, reason)
    return ok, reason


def reset_availability_cache() -> None:
    global _availability
    _availability = None


def _run_python_sync(
    code: str, files: list[tuple[str, Path]], image: str, timeout: int, memory: str
) -> RunResult:
    work = Path(tempfile.mkdtemp(prefix="vortex-run-"))
    data, out = work / "data", work / "out"
    data.mkdir()
    out.mkdir()
    try:
        for name, path in files:
            if path.exists():
                shutil.copyfile(path, data / name)
        name = f"vortex-run-{uuid.uuid4().hex[:12]}"
        args = [
            "docker", "run", "--rm", "-i", "--name", name,
            "--network", "none",
            "--read-only", "--tmpfs", "/tmp:rw,size=64m",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--memory", memory, "--memory-swap", memory, "--cpus", "1", "--pids-limit", "128",
            "-v", f"{data}:/data:ro", "-v", f"{out}:/out:rw",
            image,
        ]  # fmt: skip
        started = time.perf_counter()
        # +15 s covers container start-up; the code itself gets `timeout`.
        code_rc, stdout, stderr, timed_out = _run(args, stdin=code.encode(), timeout=timeout + 15)
        if timed_out:
            _run(["docker", "kill", name], timeout=15)
        duration = time.perf_counter() - started

        images = []
        for png in sorted(out.glob("*.png"))[:MAX_IMAGES]:
            if png.stat().st_size < 10 * 1024 * 1024:
                images.append((png.name, png.read_bytes()))
        err = stderr.decode(errors="replace")
        if timed_out:
            err += f"\n[Tempo esgotado: o código passou de {timeout} s e foi interrompido.]"
        return RunResult(
            exit_code=code_rc,
            stdout=stdout.decode(errors="replace")[:MAX_OUTPUT],
            stderr=err[-MAX_OUTPUT:],
            duration=round(duration, 2),
            timed_out=timed_out,
            images=images,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


async def run_python(
    code: str, files: list[tuple[str, Path]], *, image: str, time_limit: int, memory: str
) -> RunResult:
    return await asyncio.to_thread(_run_python_sync, code, files, image, time_limit, memory)
