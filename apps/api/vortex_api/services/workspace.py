"""Per-user settings, server settings and the tool catalog."""

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..models_db import ServerSetting, UserSettings

# Every tool the platform knows about. `step` = roadmap step that delivers it; tools only run
# when delivered AND enabled by the user AND (for heavy ones) the server has what they need.
TOOLS: list[dict[str, Any]] = [
    {
        "id": "web_search",
        "label": "Navegação Web",
        "step": 6,
        "description": "Pesquisa na web com SearXNG local e leitura de páginas, com fontes.",
    },
    {
        "id": "image_generation",
        "label": "Geração de Imagens",
        "step": 6,
        "description": "Cria imagens localmente com Stable Diffusion (ComfyUI).",
    },
    {
        "id": "video_generation",
        "label": "Geração de Vídeos",
        "step": 8,
        "description": "Cria vídeos curtos localmente (precisa de GPU NVIDIA).",
    },
    {
        "id": "file_analysis",
        "label": "Análise de Arquivos",
        "step": 5,
        "description": "Lê PDF, DOCX, planilhas e imagens enviados na conversa.",
    },
    {
        "id": "ocr",
        "label": "OCR e Texto",
        "step": 5,
        "description": "Extrai texto de imagens e PDFs escaneados.",
    },
    {
        "id": "data",
        "label": "Dados e Planilhas",
        "step": 6,
        "description": "Analisa dados e gera gráficos com Python isolado.",
    },
    {
        "id": "code",
        "label": "Programação",
        "step": 6,
        "description": "Executa código em um ambiente isolado.",
    },
    {
        "id": "agents",
        "label": "Agentes IA",
        "step": 7,
        "description": "Agentes com instruções, ferramentas e conhecimento próprios.",
    },
    {
        "id": "automations",
        "label": "Automatizações",
        "step": 7,
        "description": "Fluxos automáticos com gatilhos e ações.",
    },
]
TOOL_IDS = {t["id"] for t in TOOLS}

# Steps already delivered; bumped as each step lands.
DELIVERED_STEP = 5


def tool_catalog(enabled: dict[str, bool]) -> list[dict[str, Any]]:
    return [
        {
            **t,
            "available": t["step"] <= DELIVERED_STEP,
            "enabled": enabled.get(t["id"], True),
        }
        for t in TOOLS
    ]


async def user_settings(session: AsyncSession, user_id: str) -> UserSettings:
    """The user's settings row, or an unsaved default one."""
    row = await session.get(UserSettings, user_id)
    if row is None:
        row = UserSettings(
            user_id=user_id,
            custom_instructions="",
            tools={},
            memory_enabled=True,
            language="pt-BR",
        )
    return row


async def get_server_setting(session: AsyncSession, key: str) -> str | None:
    row = await session.get(ServerSetting, key)
    return row.value if row else None


async def set_server_setting(session: AsyncSession, key: str, value: str) -> None:
    row = await session.get(ServerSetting, key)
    if row:
        row.value = value
    else:
        session.add(ServerSetting(key=key, value=value))


async def registration_open(request: Request, session: AsyncSession) -> bool:
    """Admin override from the settings page wins over VORTEX_ALLOW_REGISTRATION."""
    value = await get_server_setting(session, "allow_registration")
    if value is None:
        return request.app.state.settings.allow_registration
    return value == "true"
