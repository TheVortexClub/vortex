"use client";

import {
  Bot,
  Code,
  FileSearch,
  FileText,
  Image as ImageIcon,
  type LucideIcon,
  Play,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import type { Mode } from "@/lib/api";
import { VortexSwirl } from "../vortex-swirl";
import { MODES } from "./modes";

const SUGGESTIONS: { text: string; icon: LucideIcon; mode: Mode }[] = [
  { text: "Me ajude a planejar um projeto", icon: Sparkles, mode: "planejar" },
  { text: "Crie uma imagem realista", icon: ImageIcon, mode: "criar" },
  { text: "Analise este arquivo", icon: FileSearch, mode: "analisar" },
  { text: "Escreva um código", icon: Code, mode: "programar" },
  { text: "Resuma este PDF", icon: FileText, mode: "analisar" },
  { text: "Crie um agente para redes sociais", icon: Bot, mode: "automatizar" },
];

export function Hero() {
  return (
    <div className="flex flex-col items-center text-center">
      <VortexSwirl className="h-[150px] w-[300px] sm:h-[200px] sm:w-[400px]" />
      <h1 className="vx-title -mt-6 text-5xl font-extralight tracking-[0.32em] sm:text-7xl">VORTEX</h1>
      <p className="mt-2 text-2xl font-light tracking-wider vx-version">
        v0.2.1
      </p>
      <p className="mt-3 text-lg text-muted sm:text-xl">Muito mais que um chatbot. Um universo de possibilidades.</p>
    </div>
  );
}

export function ActionCards({ active, onPick }: { active: Mode; onPick: (mode: Mode) => void }) {
  return (
    <div className="grid grid-cols-3 gap-2 sm:gap-3 xl:grid-cols-6">
      {MODES.map(({ id, title, description, icon: Icon, color }) => (
        <button
          key={id}
          type="button"
          onClick={() => onPick(id)}
          aria-pressed={active === id}
          className={`vx-panel flex flex-col items-center gap-2 px-3 py-3 text-center sm:py-4 transition hover:-translate-y-0.5 hover:border-line-strong ${
            active === id && id !== "conversar" ? "vx-active" : ""
          }`}
        >
          <Icon className={`size-7 ${color}`} />
          <span className="font-semibold">{title}</span>
          <span className="hidden text-xs leading-snug text-muted sm:block">{description}</span>
        </button>
      ))}
    </div>
  );
}

export function SuggestionChips({ onPick }: { onPick: (text: string, mode: Mode) => void }) {
  return (
    <div className="mx-auto grid max-w-3xl grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {SUGGESTIONS.map(({ text, icon: Icon, mode }) => (
        <button
          key={text}
          type="button"
          onClick={() => onPick(text, mode)}
          className="flex items-center gap-2.5 rounded-xl border border-line bg-panel px-3.5 py-2.5 text-left text-sm text-muted transition hover:border-line-strong hover:text-fg"
        >
          <Icon className="size-4 shrink-0" />
          <span className="truncate">{text}</span>
        </button>
      ))}
    </div>
  );
}

export function ShowcaseCards() {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <Link
        href="/criar"
        className="group relative h-28 overflow-hidden rounded-2xl border border-line"
        aria-label="Imagens incríveis"
      >
        <div className="absolute inset-0 bg-[radial-gradient(120%_90%_at_80%_100%,#f59e0b_0%,#c2410c_25%,#6d28d9_55%,#0b1020_85%)]" />
        <svg viewBox="0 0 200 60" preserveAspectRatio="none" className="absolute bottom-0 h-1/2 w-full" aria-hidden="true">
          <path d="M0 60 L0 40 L40 30 L70 38 L110 14 L130 22 L160 8 L200 34 L200 60Z" fill="#0b0a1f" opacity="0.85" />
        </svg>
        <ShowcaseText title="Imagens incríveis" text="Crie imagens realistas, artísticas ou conceituais com o Vortex." />
      </Link>
      <Link href="/criar" className="group relative h-28 overflow-hidden rounded-2xl border border-line" aria-label="Vídeos com IA">
        <div className="absolute inset-0 bg-[linear-gradient(120deg,#0b1020_40%,#1e293b_70%,#334155)]" />
        <div className="absolute right-5 top-1/2 grid size-12 -translate-y-1/2 place-items-center rounded-full border border-white/40 bg-black/40 text-white">
          <Play className="size-5 fill-current" />
        </div>
        <span className="absolute bottom-2 right-3 rounded bg-black/60 px-1.5 text-[10px] text-white">00:28</span>
        <ShowcaseText title="Vídeos com IA" text="Transforme ideias em vídeos de alta qualidade." />
      </Link>
      <Link
        href="/agentes"
        className="group relative h-28 overflow-hidden rounded-2xl border border-line"
        aria-label="Agentes personalizados"
      >
        <div className="absolute inset-0 bg-[radial-gradient(80%_120%_at_90%_40%,#1d4ed8_0%,#0b1430_55%,#060a18_100%)]" />
        <Bot className="absolute -right-2 top-1/2 size-24 -translate-y-1/2 text-sky-300/80 drop-shadow-[0_0_20px_rgba(56,189,248,0.7)]" />
        <ShowcaseText title="Agentes personalizados" text="Crie agentes para automatizar tarefas e fluxos de trabalho." />
      </Link>
    </div>
  );
}

function ShowcaseText({ title, text }: { title: string; text: string }) {
  return (
    <div className="relative max-w-[65%] p-4 text-white">
      <p className="font-semibold">{title}</p>
      <p className="mt-1 text-xs leading-snug text-white/75">{text}</p>
    </div>
  );
}
