"""Image generation through a local ComfyUI server (Stable Diffusion), via its HTTP API."""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from collections.abc import Awaitable, Callable

import httpx

POLL_SECONDS = 2.0
MAX_WAIT_SECONDS = 45 * 60  # CPU-only servers can take many minutes
SECONDS_PER_STEP_GUESS = 6.0  # used only for the progress estimate on CPU


class ImageError(Exception):
    pass


def txt2img_workflow(
    prompt: str,
    negative: str,
    width: int,
    height: int,
    steps: int,
    seed: int | None,
    checkpoint: str,
) -> dict:
    """The standard ComfyUI text-to-image graph."""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed if seed is not None else random.randint(0, 2**31 - 1),
                "steps": steps,
                # SD-Turbo / SDXL-Turbo want cfg 1 (and only 1-4 steps): much faster on CPU
                "cfg": 1.0 if "turbo" in checkpoint.lower() else 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "vortex", "images": ["8", 0]},
        },
    }


async def comfy_status(client: httpx.AsyncClient, url: str) -> tuple[bool, str]:
    try:
        r = await client.get(f"{url.rstrip('/')}/system_stats", timeout=3.0)
        r.raise_for_status()
        return True, "pronto"
    except (httpx.HTTPError, ValueError):
        return False, "O ComfyUI (gerador de imagens) não está rodando no servidor."


async def generate(
    client: httpx.AsyncClient,
    url: str,
    workflow: dict,
    on_progress: Callable[[float], Awaitable[None]],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> list[tuple[str, bytes]]:
    base = url.rstrip("/")
    try:
        r = await client.post(
            f"{base}/prompt", json={"prompt": workflow, "client_id": uuid.uuid4().hex}, timeout=30
        )
    except httpx.HTTPError as e:
        raise ImageError("O ComfyUI não respondeu.") from e
    if r.status_code >= 400:
        detail = r.text[:300]
        if "ckpt_name" in detail or "not in" in detail:
            raise ImageError(
                "O modelo de imagem configurado não foi encontrado no ComfyUI "
                "(veja VORTEX_IMAGE_CHECKPOINT)."
            )
        raise ImageError(f"O ComfyUI recusou o pedido: {detail}")
    prompt_id = r.json()["prompt_id"]

    steps = workflow["3"]["inputs"]["steps"]
    expected = max(steps * SECONDS_PER_STEP_GUESS, 10)
    started = time.monotonic()
    while True:
        elapsed = time.monotonic() - started
        if elapsed > MAX_WAIT_SECONDS:
            raise ImageError("A geração demorou demais e foi cancelada.")
        try:
            history = (await client.get(f"{base}/history/{prompt_id}", timeout=15)).json()
        except (httpx.HTTPError, ValueError) as e:
            raise ImageError("Perdi a conexão com o ComfyUI.") from e
        entry = history.get(prompt_id)
        if entry:
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise ImageError("O ComfyUI falhou ao gerar a imagem.")
            if status.get("completed", True):
                break
        await on_progress(min(0.95, elapsed / expected))
        await sleep(POLL_SECONDS)

    images = []
    for output in entry.get("outputs", {}).values():
        for img in output.get("images", []):
            r = await client.get(
                f"{base}/view",
                params={
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                },
                timeout=60,
            )
            r.raise_for_status()
            images.append((img["filename"], r.content))
    if not images:
        raise ImageError("O ComfyUI terminou sem devolver imagens.")
    return images
