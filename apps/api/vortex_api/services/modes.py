"""Chat modes picked by the home action cards, and the "Pensar" (think) toggle."""

from typing import Literal

Mode = Literal["conversar", "criar", "analisar", "programar", "planejar", "automatizar"]

MODE_INSTRUCTIONS: dict[str, str | None] = {
    "conversar": None,
    "criar": (
        "Modo Criar: ajude o usuário a criar textos, ideias e conteúdos originais. "
        "Seja criativo e ofereça variações quando fizer sentido."
    ),
    "analisar": (
        "Modo Analisar: analise com rigor. Estruture a resposta em tópicos, destaque dados, "
        "riscos e conclusões, e diga o que falta para uma análise completa."
    ),
    "programar": (
        "Modo Programar: aja como um engenheiro de software sênior. Escreva código correto e "
        "completo em blocos com a linguagem indicada e explique as decisões em poucas linhas."
    ),
    "planejar": (
        "Modo Planejar: organize em etapas, prioridades e prazos. Use listas numeradas e "
        "tabelas quando ajudarem."
    ),
    "automatizar": (
        "Modo Automatizar: ajude a desenhar automações e fluxos de trabalho, com gatilhos, "
        "ações e condições concretas."
    ),
}

THINK_INSTRUCTION = (
    "Antes de responder, raciocine passo a passo entre <think> e </think>. "
    "Depois de </think>, escreva apenas a resposta final."
)


def system_instructions(mode: str, think: bool) -> str | None:
    parts = [MODE_INSTRUCTIONS.get(mode), THINK_INSTRUCTION if think else None]
    text = "\n\n".join(p for p in parts if p)
    return text or None
