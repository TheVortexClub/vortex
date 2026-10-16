"""Hardware stats for the usage dashboard: CPU, RAM, GPU, and what the model server has loaded."""

import functools
import platform
import shutil
import subprocess
import sys
from typing import Any

import httpx
import psutil

psutil.cpu_percent(interval=None)  # prime the counter; the first reading is always 0


def _run(cmd: list[str], timeout: float = 4.0) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
        return out.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _nvidia() -> list[dict[str, Any]]:
    if not shutil.which("nvidia-smi"):
        return []
    out = _run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    gpus = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 4:
            name, total, used, util = parts
            gpus.append(
                {
                    "name": name,
                    "memory_total_mb": float(total),
                    "memory_used_mb": float(used),
                    "utilization": float(util),
                    "compute": "CUDA",
                }
            )
    return gpus


@functools.lru_cache(maxsize=1)
def _other_gpus() -> tuple[str, ...]:
    """GPU names without live stats (AMD/Intel). Cached: this query is slow on Windows."""
    if sys.platform == "win32":
        out = _run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_VideoController).Name",
            ],
            timeout=8,
        )
        names = [n.strip() for n in out.splitlines() if n.strip()]
        return tuple(n for n in names if "virtual" not in n.lower() and "basic" not in n.lower())
    return ()


def hardware() -> dict[str, Any]:
    mem = psutil.virtual_memory()
    gpus = _nvidia()
    if not gpus:
        gpus = [
            {
                "name": n,
                "memory_total_mb": None,
                "memory_used_mb": None,
                "utilization": None,
                "compute": None,
            }
            for n in _other_gpus()
        ]
    return {
        "platform": f"{platform.system()} {platform.release()}",
        "cpu": {
            "name": platform.processor() or platform.machine(),
            "cores": psutil.cpu_count(logical=True),
            "percent": psutil.cpu_percent(interval=None),
        },
        "memory": {
            "total_gb": round(mem.total / 1024**3, 1),
            "used_gb": round((mem.total - mem.available) / 1024**3, 1),
            "percent": mem.percent,
        },
        "gpus": gpus,
    }


async def ollama_loaded(base_url: str) -> list[dict[str, Any]] | None:
    """Models Ollama currently holds in memory, and whether they run on CPU or GPU."""
    root = base_url.rstrip("/").removesuffix("/v1")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            data = (await client.get(f"{root}/api/ps")).json()
    except (httpx.HTTPError, ValueError):
        return None
    models = []
    for m in data.get("models", []):
        size, vram = m.get("size") or 0, m.get("size_vram") or 0
        share = round(100 * vram / size) if size else 0
        models.append(
            {
                "name": m.get("name"),
                "size_gb": round(size / 1024**3, 1),
                "processor": "CPU" if share == 0 else ("GPU" if share >= 99 else f"{share}% GPU"),
            }
        )
    return models
