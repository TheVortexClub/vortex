"use client";

import {
  ArrowUp,
  Brain,
  ChevronDown,
  FileUp,
  Image as ImageIcon,
  Mic,
  Music,
  Plus,
  Search,
  Square,
  Wrench,
  X,
} from "lucide-react";
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import type { Mode, ModelInfo } from "@/lib/api";
import { MODES } from "./modes";

export type ComposerHandle = { focus: () => void; setText: (text: string) => void };

type Props = {
  onSend: (text: string) => void;
  onStop: () => void;
  streaming: boolean;
  think: boolean;
  onThink: (on: boolean) => void;
  mode: Mode;
  onClearMode: () => void;
  models: ModelInfo[];
  model: string | null;
  onModel: (id: string) => void;
  compact?: boolean;
};

const soon = (what: string, step: number) => `${what} — chega na etapa ${step}`;

export const Composer = forwardRef<ComposerHandle, Props>(function Composer(
  { onSend, onStop, streaming, think, onThink, mode, onClearMode, models, model, onModel, compact },
  ref,
) {
  const [text, setText] = useState("");
  const [attachOpen, setAttachOpen] = useState(false);
  const area = useRef<HTMLTextAreaElement>(null);
  const attachRef = useRef<HTMLDivElement>(null);

  useImperativeHandle(ref, () => ({
    focus: () => area.current?.focus(),
    setText: (t: string) => {
      setText(t);
      requestAnimationFrame(() => {
        area.current?.focus();
        area.current?.setSelectionRange(t.length, t.length);
      });
    },
  }));

  // auto-grow
  useEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 260)}px`;
  }, [text]);

  useEffect(() => {
    if (!attachOpen) return;
    const onDown = (e: MouseEvent) => {
      if (attachRef.current && !attachRef.current.contains(e.target as Node)) setAttachOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [attachOpen]);

  const submit = () => {
    if (streaming || !text.trim()) return;
    onSend(text.trim());
    setText("");
  };

  const modeInfo = MODES.find((m) => m.id === mode);
  const selected = models.find((m) => m.id === model) ?? models.find((m) => m.default);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className={`vx-glow-border rounded-2xl bg-panel backdrop-blur-xl ${compact ? "p-3" : "p-4"}`}
    >
      {mode !== "conversar" && modeInfo && (
        <div className="mb-2 flex">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-accent/15 px-2.5 py-1 text-xs text-accent">
            <modeInfo.icon className="size-3.5" /> Modo {modeInfo.title}
            <button type="button" onClick={onClearMode} aria-label="Sair do modo" className="ml-1 hover:text-fg">
              <X className="size-3.5" />
            </button>
          </span>
        </div>
      )}
      <label htmlFor="vx-input" className="sr-only">
        Mensagem para o Vortex
      </label>
      <textarea
        id="vx-input"
        ref={area}
        value={text}
        rows={compact ? 1 : 2}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder={modeInfo?.placeholder ?? "Digite sua mensagem para o Vortex..."}
        className="vx-scroll w-full resize-none bg-transparent px-1 focus-visible:outline-none text-[15px] leading-relaxed outline-none placeholder:text-subtle"
      />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <div className="relative" ref={attachRef}>
          <button
            type="button"
            onClick={() => setAttachOpen((o) => !o)}
            className="grid size-10 place-items-center rounded-xl text-muted hover:bg-chip hover:text-fg"
            aria-label="Anexar"
            aria-expanded={attachOpen}
          >
            <Plus className="size-5" />
          </button>
          {attachOpen && (
            <div className="vx-panel absolute bottom-12 left-0 z-30 w-60 p-1 text-sm shadow-2xl" role="menu">
              {[
                { icon: FileUp, label: "Arquivos (PDF, DOCX, planilhas)" },
                { icon: ImageIcon, label: "Imagens" },
                { icon: Music, label: "Áudio" },
              ].map(({ icon: Icon, label }) => (
                <button
                  key={label}
                  type="button"
                  disabled
                  role="menuitem"
                  title={soon("Envio de arquivos", 5)}
                  className="flex w-full cursor-not-allowed items-center gap-2 rounded-md px-2.5 py-2 text-left text-subtle"
                >
                  <Icon className="size-4" /> {label}
                  <span className="ml-auto text-[10px]">etapa 5</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <Toggle icon={Search} label="Pesquisar" disabled title={soon("Pesquisa na web (SearXNG local)", 6)} />
        <Toggle
          icon={Brain}
          label="Pensar"
          active={think}
          onClick={() => onThink(!think)}
          title="O Vortex raciocina passo a passo antes de responder"
        />
        <Toggle icon={Wrench} label="Ferramentas" disabled title={soon("Ferramentas", 6)} />

        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <select
              value={selected?.id ?? ""}
              onChange={(e) => onModel(e.target.value)}
              aria-label="Modelo"
              className="h-10 appearance-none rounded-xl border border-line bg-elev/70 pl-3 pr-9 text-sm outline-none hover:border-line-strong"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.display_name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-subtle" />
          </div>
          <button
            type="button"
            disabled
            title={soon("Voz para texto com Whisper local", 5)}
            aria-label="Microfone (em breve)"
            className="grid size-10 cursor-not-allowed place-items-center rounded-xl text-subtle"
          >
            <Mic className="size-5" />
          </button>
          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Parar resposta"
              className="grid size-10 place-items-center rounded-full bg-fg text-bg transition hover:opacity-90"
            >
              <Square className="size-4 fill-current" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!text.trim()}
              aria-label="Enviar"
              className="grid size-10 place-items-center rounded-full bg-accent text-white shadow-[0_0_20px_var(--accent-glow)] transition hover:brightness-110 disabled:opacity-40 disabled:shadow-none"
            >
              <ArrowUp className="size-5" />
            </button>
          )}
        </div>
      </div>
    </form>
  );
});

function Toggle({
  icon: Icon,
  label,
  active,
  disabled,
  onClick,
  title,
}: {
  icon: typeof Search;
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  title: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active ?? false}
      title={title}
      className={`flex h-10 items-center gap-2 rounded-xl border px-3.5 text-sm transition ${
        active
          ? "border-accent bg-accent/15 text-fg"
          : "border-line bg-elev/50 text-muted hover:text-fg"
      } disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:text-muted`}
    >
      <Icon className="size-4" />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
