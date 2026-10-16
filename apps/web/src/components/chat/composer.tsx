"use client";

import {
  AlertCircle,
  ArrowUp,
  Brain,
  ChevronDown,
  FileText,
  FileUp,
  Image as ImageIcon,
  Loader2,
  Mic,
  Music,
  Plus,
  Search,
  Square,
  Wrench,
  X,
} from "lucide-react";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import {
  ACCEPTED_FILES,
  api,
  type Attachment,
  errorMessage,
  formatSize,
  type Mode,
  type ModelInfo,
  uploadFile,
  waitForFile,
} from "@/lib/api";
import { useWorkspace } from "../workspace";
import { MODES } from "./modes";

export type ComposerHandle = {
  focus: () => void;
  setText: (text: string) => void;
  addFiles: (files: File[]) => void;
  pickFiles: () => void;
};

type Pending = {
  key: string;
  name: string;
  size: number;
  status: "uploading" | "processing" | "ready" | "error";
  error?: string;
  info?: Attachment;
  ocr?: boolean;
};

type Props = {
  onSend: (text: string, attachments: Attachment[]) => void;
  onStop: () => void;
  streaming: boolean;
  think: boolean;
  onThink: (on: boolean) => void;
  webSearch: boolean;
  onWebSearch: (on: boolean) => void;
  toolsOn: boolean;
  onTools: (on: boolean) => void;
  mode: Mode;
  onClearMode: () => void;
  models: ModelInfo[];
  model: string | null;
  onModel: (id: string) => void;
  /** Where uploads belong (the current conversation, if it exists yet). */
  conversationId?: string | null;
  compact?: boolean;
};

const soon = (what: string, step: number) => `${what} — chega na etapa ${step}`;

export const Composer = forwardRef<ComposerHandle, Props>(function Composer(
  {
    onSend,
    onStop,
    streaming,
    think,
    onThink,
    webSearch,
    onWebSearch,
    toolsOn,
    onTools,
    mode,
    onClearMode,
    models,
    model,
    onModel,
    conversationId,
    compact,
  },
  ref,
) {
  const { tools } = useWorkspace();
  const tool = (id: string) => tools.find((t) => t.id === id);
  const web = tool("web_search");
  const anyTool = ["image_generation", "code"].map(tool).find((t) => t?.available && t.enabled);
  const toolsHelp = ["image_generation", "code"]
    .map(tool)
    .filter(Boolean)
    .map((t) => `${t!.label}: ${t!.available ? (t!.enabled ? "pronta" : "desligada") : t!.reason}`)
    .join("\n");
  const [text, setText] = useState("");
  const [files, setFiles] = useState<Pending[]>([]);
  const [attachOpen, setAttachOpen] = useState(false);
  const [dragging, setDragging] = useState(false);
  const area = useRef<HTMLTextAreaElement>(null);
  const attachRef = useRef<HTMLDivElement>(null);
  const picker = useRef<HTMLInputElement>(null);

  const patch = (key: string, change: Partial<Pending>) =>
    setFiles((fs) => fs.map((f) => (f.key === key ? { ...f, ...change } : f)));

  const addFiles = useCallback(
    (list: File[]) => {
      for (const file of list.slice(0, 10)) {
        const key = `${file.name}-${file.size}-${Math.random()}`;
        setFiles((fs) => [...fs, { key, name: file.name, size: file.size, status: "uploading" }]);
        void (async () => {
          try {
            const uploaded = await uploadFile(file, { conversation_id: conversationId });
            patch(key, { status: "processing" });
            const done = await waitForFile(uploaded.id);
            patch(key, {
              status: done.status === "ready" ? "ready" : "error",
              error: done.error ?? undefined,
              ocr: done.ocr,
              info: { id: done.id, name: done.name, kind: done.kind, size: done.size },
            });
          } catch (e) {
            patch(key, { status: "error", error: errorMessage(e) });
          }
        })();
      }
    },
    [conversationId],
  );

  useImperativeHandle(ref, () => ({
    focus: () => area.current?.focus(),
    setText: (t: string) => {
      setText(t);
      requestAnimationFrame(() => {
        area.current?.focus();
        area.current?.setSelectionRange(t.length, t.length);
      });
    },
    addFiles,
    pickFiles: () => picker.current?.click(),
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

  const busyFiles = files.some((f) => f.status === "uploading" || f.status === "processing");
  const ready = files.filter((f) => f.status === "ready" && f.info).map((f) => f.info as Attachment);

  const submit = () => {
    if (streaming || busyFiles || !text.trim()) return;
    onSend(text.trim(), ready);
    setText("");
    setFiles([]);
  };

  const removeFile = (f: Pending) => {
    setFiles((fs) => fs.filter((x) => x.key !== f.key));
    if (f.info) void api(`/api/files/${f.info.id}`, { method: "DELETE" }).catch(() => {});
  };

  const modeInfo = MODES.find((m) => m.id === mode);
  const selected = models.find((m) => m.id === model) ?? models.find((m) => m.default);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      onDragOver={(e) => {
        if (e.dataTransfer.types.includes("Files")) {
          e.preventDefault();
          setDragging(true);
        }
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        if (!e.dataTransfer.files.length) return;
        e.preventDefault();
        setDragging(false);
        addFiles(Array.from(e.dataTransfer.files));
      }}
      className={`vx-glow-border relative rounded-2xl bg-panel backdrop-blur-xl ${compact ? "p-3" : "p-4"} ${
        dragging ? "ring-2 ring-accent" : ""
      }`}
    >
      {dragging && (
        <div className="pointer-events-none absolute inset-0 z-10 grid place-items-center rounded-2xl bg-bg/80 text-sm text-accent">
          Solte os arquivos para anexar
        </div>
      )}
      <input
        ref={picker}
        type="file"
        multiple
        hidden
        accept={ACCEPTED_FILES}
        onChange={(e) => {
          addFiles(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
      />

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

      {files.length > 0 && (
        <ul className="mb-2 flex flex-wrap gap-2" aria-label="Anexos">
          {files.map((f) => (
            <li
              key={f.key}
              className={`flex max-w-64 items-center gap-2 rounded-xl border px-2.5 py-1.5 text-xs ${
                f.status === "error" ? "border-bad/50 bg-bad/10" : "border-line bg-elev/70"
              }`}
              title={f.error ?? (f.ocr ? "Texto lido com OCR" : undefined)}
            >
              {f.status === "uploading" || f.status === "processing" ? (
                <Loader2 className="size-4 shrink-0 animate-spin text-accent" />
              ) : f.status === "error" ? (
                <AlertCircle className="size-4 shrink-0 text-bad" />
              ) : (
                <FileText className="size-4 shrink-0 text-accent" />
              )}
              <span className="min-w-0">
                <span className="block truncate">{f.name}</span>
                <span className="block text-subtle">
                  {f.status === "uploading"
                    ? "enviando…"
                    : f.status === "processing"
                      ? "lendo o conteúdo…"
                      : f.status === "error"
                        ? f.error ?? "erro"
                        : `${formatSize(f.size)}${f.ocr ? " • OCR" : ""}`}
                </span>
              </span>
              <button type="button" onClick={() => removeFile(f)} aria-label={`Remover ${f.name}`} className="hover:text-fg">
                <X className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
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
        onPaste={(e) => {
          const pasted = Array.from(e.clipboardData.files);
          if (pasted.length) {
            e.preventDefault();
            addFiles(pasted);
          }
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder={modeInfo?.placeholder ?? "Digite sua mensagem para o Vortex..."}
        className="vx-scroll w-full resize-none bg-transparent px-1 text-[15px] leading-relaxed outline-none focus-visible:outline-none placeholder:text-subtle"
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
            <div className="vx-panel absolute bottom-12 left-0 z-30 w-64 p-1 text-sm shadow-2xl" role="menu">
              {[
                { icon: FileUp, label: "Arquivos (PDF, Word, planilhas, código)" },
                { icon: ImageIcon, label: "Imagens (lê o texto com OCR)" },
              ].map(({ icon: Icon, label }) => (
                <button
                  key={label}
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setAttachOpen(false);
                    picker.current?.click();
                  }}
                  className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left hover:bg-chip"
                >
                  <Icon className="size-4" /> {label}
                </button>
              ))}
              <button
                type="button"
                disabled
                role="menuitem"
                title={soon("Transcrição de áudio com Whisper local", 8)}
                className="flex w-full cursor-not-allowed items-center gap-2 rounded-md px-2.5 py-2 text-left text-subtle"
              >
                <Music className="size-4" /> Áudio
                <span className="ml-auto text-[10px]">etapa 8</span>
              </button>
            </div>
          )}
        </div>

        <Toggle
          icon={Search}
          label="Pesquisar"
          active={webSearch}
          disabled={!web?.available || !web.enabled}
          onClick={() => onWebSearch(!webSearch)}
          title={
            !web
              ? "Pesquisa na web"
              : !web.enabled
                ? "Pesquisa na web desligada em Configurações > Ferramentas"
                : web.available
                  ? "Pesquisar na web (SearXNG local) antes de responder, citando as fontes"
                  : web.reason
          }
        />
        <Toggle
          icon={Brain}
          label="Pensar"
          active={think}
          onClick={() => onThink(!think)}
          title="O Vortex raciocina passo a passo antes de responder"
        />
        <Toggle
          icon={Wrench}
          label="Ferramentas"
          active={toolsOn}
          disabled={!anyTool}
          onClick={() => onTools(!toolsOn)}
          title={`Gerar imagens ("crie uma imagem de…") e escrever código executável
${toolsHelp}`}
        />

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
            title={soon("Voz para texto com Whisper local", 8)}
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
              disabled={!text.trim() || busyFiles}
              aria-label={busyFiles ? "Aguardando arquivos" : "Enviar"}
              className="grid size-10 place-items-center rounded-full bg-accent text-white shadow-[0_0_20px_var(--accent-glow)] transition hover:brightness-110 disabled:opacity-40 disabled:shadow-none"
            >
              {busyFiles ? <Loader2 className="size-5 animate-spin" /> : <ArrowUp className="size-5" />}
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
