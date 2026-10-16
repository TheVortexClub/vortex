"use client";

import { motion } from "framer-motion";
import {
  Brain,
  Check,
  ChevronDown,
  Copy,
  GitBranch,
  Pencil,
  RefreshCw,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { useState } from "react";
import type { Message } from "@/lib/api";
import { copyText, splitThinking } from "@/lib/text";
import { VortexMark } from "../brand";
import { Markdown } from "./markdown";

export type DisplayMessage = Pick<Message, "id" | "role" | "content" | "reasoning" | "status" | "feedback"> & {
  streaming?: boolean;
};

type Actions = {
  onRegenerate?: () => void;
  onEdit?: (id: string, content: string) => void;
  onFeedback?: (id: string, value: number) => void;
  onBranch?: (id: string) => void;
  busy: boolean;
};

export function MessageView({ message, isLast, actions }: { message: DisplayMessage; isLast: boolean; actions: Actions }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={message.role === "user" ? "flex justify-end" : "flex gap-3"}
    >
      {message.role === "user" ? (
        <UserMessage message={message} actions={actions} />
      ) : (
        <AssistantMessage message={message} isLast={isLast} actions={actions} />
      )}
    </motion.div>
  );
}

function UserMessage({ message, actions }: { message: DisplayMessage; actions: Actions }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);
  const canEdit = !actions.busy && !message.id.startsWith("tmp-") && actions.onEdit;

  if (editing) {
    return (
      <form
        className="w-full max-w-[80%] space-y-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!draft.trim()) return;
          setEditing(false);
          actions.onEdit?.(message.id, draft.trim());
        }}
      >
        <textarea
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={Math.min(8, draft.split("\n").length + 1)}
          aria-label="Editar mensagem"
          className="w-full rounded-2xl border border-accent bg-elev p-3 text-[15px] outline-none"
        />
        <div className="flex justify-end gap-2 text-sm">
          <button type="button" onClick={() => setEditing(false)} className="rounded-lg px-3 py-1.5 hover:bg-chip">
            Cancelar
          </button>
          <button type="submit" className="rounded-lg bg-accent px-3 py-1.5 text-white">
            Enviar
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="group flex max-w-[85%] flex-col items-end gap-1">
      <div className="whitespace-pre-wrap rounded-2xl rounded-br-md border border-accent/30 bg-accent/15 px-4 py-2.5 text-[15px] leading-relaxed">
        {message.content}
      </div>
      {canEdit && (
        <div className="flex gap-1 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
          <IconButton label="Copiar" icon={Copy} onClick={() => void copyText(message.content)} />
          <IconButton
            label="Editar"
            icon={Pencil}
            onClick={() => {
              setDraft(message.content);
              setEditing(true);
            }}
          />
        </div>
      )}
    </div>
  );
}

function AssistantMessage({ message, isLast, actions }: { message: DisplayMessage; isLast: boolean; actions: Actions }) {
  const [copied, setCopied] = useState(false);
  const parsed = splitThinking(message.content);
  const thinking = [message.reasoning, parsed.thinking].filter(Boolean).join("\n\n");
  const answer = parsed.answer;
  const stillThinking = message.streaming && (parsed.open || (!!message.reasoning && !answer));
  const saved = !message.streaming && !message.id.startsWith("tmp-");

  return (
    <>
      <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-xl border border-line bg-elev">
        <VortexMark className="size-6" />
      </span>
      <div className="min-w-0 flex-1 pt-1">
        {thinking && <ThinkingPanel text={thinking} active={!!stillThinking} />}
        {answer ? (
          <div className={message.streaming ? "vx-cursor" : ""}>
            <Markdown text={answer} />
          </div>
        ) : (
          message.streaming &&
          !thinking && (
            <p className="flex items-center gap-2 text-muted" role="status">
              <span className="inline-flex gap-1">
                <span className="size-1.5 animate-bounce rounded-full bg-accent [animation-delay:-0.2s]" />
                <span className="size-1.5 animate-bounce rounded-full bg-accent [animation-delay:-0.1s]" />
                <span className="size-1.5 animate-bounce rounded-full bg-accent" />
              </span>
              Pensando...
            </p>
          )
        )}
        {message.status === "cancelled" && !message.streaming && (
          <p className="mt-2 text-xs text-warn">Resposta interrompida.</p>
        )}
        {saved && (
          <div className="mt-2 flex flex-wrap gap-1 text-subtle">
            <IconButton
              label={copied ? "Copiado" : "Copiar"}
              icon={copied ? Check : Copy}
              onClick={() =>
                void copyText(answer).then(() => {
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                })
              }
            />
            {isLast && actions.onRegenerate && (
              <IconButton label="Gerar novamente" icon={RefreshCw} onClick={actions.onRegenerate} disabled={actions.busy} />
            )}
            <IconButton
              label="Gostei"
              icon={ThumbsUp}
              active={message.feedback === 1}
              onClick={() => actions.onFeedback?.(message.id, message.feedback === 1 ? 0 : 1)}
            />
            <IconButton
              label="Não gostei"
              icon={ThumbsDown}
              active={message.feedback === -1}
              onClick={() => actions.onFeedback?.(message.id, message.feedback === -1 ? 0 : -1)}
            />
            <IconButton
              label="Ramificar a partir daqui"
              icon={GitBranch}
              onClick={() => actions.onBranch?.(message.id)}
              disabled={actions.busy}
            />
          </div>
        )}
      </div>
    </>
  );
}

function ThinkingPanel({ text, active }: { text: string; active: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-3 rounded-xl border border-line bg-elev/60 text-sm">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-muted hover:text-fg"
      >
        <Brain className={`size-4 text-accent-2 ${active ? "animate-pulse" : ""}`} />
        {active ? "Pensando..." : "Raciocínio"}
        <ChevronDown className={`ml-auto size-4 transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <p className="whitespace-pre-wrap border-t border-line px-3 py-2 text-muted">{text}</p>}
    </div>
  );
}

function IconButton({
  label,
  icon: Icon,
  onClick,
  active,
  disabled,
}: {
  label: string;
  icon: typeof Copy;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      aria-pressed={active}
      className={`grid size-8 place-items-center rounded-lg transition hover:bg-chip hover:text-fg disabled:opacity-40 ${
        active ? "text-accent" : ""
      }`}
    >
      <Icon className="size-4" />
    </button>
  );
}
