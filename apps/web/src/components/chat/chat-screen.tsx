"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Brain, FolderOpen, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  type Attachment,
  type Conversation,
  errorMessage,
  type Message,
  type Mode,
  toApiError,
} from "@/lib/api";
import { readEvents } from "@/lib/sse";
import { useWorkspace } from "../workspace";
import { Composer, type ComposerHandle } from "./composer";
import { ActionCards, Hero, ShowcaseCards, SuggestionChips } from "./home";
import { RunContext } from "./markdown";
import { type DisplayMessage, MessageView } from "./message-view";

type ChatBody = {
  content?: string;
  model?: string | null;
  mode?: Mode;
  think?: boolean;
  regenerate?: boolean;
  edit_message_id?: string;
  file_ids?: string[];
  web_search?: boolean;
  tools?: boolean;
};

type Streaming = { completionId: string | null; content: string; reasoning: string };

export function ChatScreen() {
  const pathname = usePathname();
  const router = useRouter();
  const routeId = pathname.startsWith("/c/") ? decodeURIComponent(pathname.slice(3)) : null;
  const searchParams = useSearchParams();
  const newChatProject = routeId ? null : searchParams.get("projeto");
  const { models, projects, tools, refreshConversations, refreshProjects, refreshUsage } = useWorkspace();
  const codeTool = tools.find((t) => t.id === "code");
  const canRun = !!codeTool?.available && codeTool.enabled;

  const [conv, setConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState<Streaming | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("conversar");
  const [model, setModel] = useState<string | null>(null);
  const [think, setThink] = useState(false);
  const [webSearch, setWebSearch] = useState(false);
  const [toolsOn, setToolsOn] = useState(false);
  const [memoryNote, setMemoryNote] = useState<string | null>(null);

  const composer = useRef<ComposerHandle>(null);
  const streamToken = useRef(0);
  const justCreated = useRef<string | null>(null);
  const completionRef = useRef<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  // A saved answer keeps the React key of the streaming bubble it replaces (no remount/flicker).
  const liveKeys = useRef(new Map<string, string>());

  // ---------------------------------------------------------------- loading a conversation
  useEffect(() => {
    if (justCreated.current && justCreated.current === routeId) {
      justCreated.current = null;
      return;
    }
    // Leaving a conversation mid-answer: stop it (the partial answer is saved) and detach.
    if (completionRef.current) {
      void api(`/v1/chat/completions/${completionRef.current}/cancel`, { method: "POST" }).catch(() => {});
      completionRef.current = null;
    }
    streamToken.current++;
    setStreaming(null);
    setError(null);

    if (!routeId) {
      setConv(null);
      setMessages([]);
      setMode("conversar");
      return;
    }
    let cancelled = false;
    setLoading(true);
    api<Conversation & { messages: Message[] }>(`/api/conversations/${routeId}`)
      .then((data) => {
        if (cancelled) return;
        const { messages: msgs, ...c } = data;
        setConv(c);
        setMessages(msgs);
        setMode(c.mode);
        setModel(c.model);
        stickToBottom.current = true;
      })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) router.replace("/");
        else setError(errorMessage(e));
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [routeId, router]);

  // ---------------------------------------------------------------- auto-scroll
  useEffect(() => {
    const el = scroller.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  const onScroll = () => {
    const el = scroller.current;
    if (el) stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  // ---------------------------------------------------------------- streaming
  const runChat = useCallback(
    async (convId: string, body: ChatBody) => {
      const token = ++streamToken.current;
      const live = () => token === streamToken.current;
      setError(null);
      stickToBottom.current = true;
      setStreaming({ completionId: null, content: "", reasoning: "" });
      try {
        const res = await fetch(`/api/conversations/${convId}/chat`, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) throw await toApiError(res);
        for await (const { event, data } of readEvents(res)) {
          if (!live()) continue; // user moved to another chat; let the server finish saving
          const d = data as Record<string, unknown>;
          if (event === "meta") {
            completionRef.current = d.completion_id as string;
            if (d.memory_saved) setMemoryNote(d.memory_saved as string);
            setStreaming((s) => s && { ...s, completionId: d.completion_id as string });
            setConv(d.conversation as Conversation);
            const um = d.user_message as Message | null;
            if (um) {
              setMessages((ms) =>
                ms.some((m) => m.id === um.id)
                  ? ms.map((m) => (m.id === um.id ? um : m))
                  : ms.map((m) => (m.id.startsWith("tmp-") ? um : m)),
              );
            }
          } else if (event === "delta") {
            setStreaming(
              (s) =>
                s && {
                  ...s,
                  content: s.content + ((d.content as string) ?? ""),
                  reasoning: s.reasoning + ((d.reasoning as string) ?? ""),
                },
            );
          } else if (event === "error") {
            setError(d.message as string);
          } else if (event === "done") {
            const saved = d.message as Message | null;
            if (saved) {
              liveKeys.current.set(saved.id, `live-${token}`);
              setMessages((ms) => [...ms, saved]);
            }
            setStreaming(null);
          }
        }
      } catch (e) {
        if (live()) setError(errorMessage(e));
      } finally {
        if (live()) {
          setStreaming(null);
          completionRef.current = null;
        }
        void refreshConversations().catch(() => {});
        void refreshProjects().catch(() => {});
        void refreshUsage();
      }
    },
    [refreshConversations, refreshProjects, refreshUsage],
  );

  const send = async (text: string, attachments: Attachment[] = []) => {
    if (streaming) return;
    setMemoryNote(null);
    const optimistic: Message = {
      id: `tmp-${Date.now()}`,
      conversation_id: conv?.id ?? "",
      role: "user",
      content: text,
      reasoning: null,
      model: null,
      status: "ok",
      feedback: null,
      attachments,
      sources: [],
      tool: null,
      created_at: new Date().toISOString(),
    };
    setMessages((ms) => [...ms, optimistic]);
    let id = conv?.id;
    if (!id) {
      try {
        const created = await api<Conversation>("/api/conversations", {
          method: "POST",
          json: { mode, model, project_id: newChatProject },
        });
        setConv(created);
        id = created.id;
        justCreated.current = id;
        router.replace(`/c/${id}`);
      } catch (e) {
        setMessages((ms) => ms.filter((m) => m.id !== optimistic.id));
        setError(errorMessage(e));
        return;
      }
    }
    await runChat(id, {
      content: text,
      model,
      mode,
      think,
      file_ids: attachments.map((a) => a.id),
      web_search: webSearch,
      tools: toolsOn,
    });
  };

  const stop = () => {
    const id = completionRef.current;
    if (id) void api(`/v1/chat/completions/${id}/cancel`, { method: "POST" }).catch(() => {});
  };

  const regenerate = () => {
    if (!conv || streaming) return;
    setMessages((ms) => {
      const out = [...ms];
      while (out.length && out[out.length - 1].role === "assistant") out.pop();
      return out;
    });
    void runChat(conv.id, { regenerate: true, model, think, web_search: webSearch, tools: toolsOn });
  };

  const edit = (messageId: string, content: string) => {
    if (!conv || streaming) return;
    setMessages((ms) => {
      const idx = ms.findIndex((m) => m.id === messageId);
      return idx < 0 ? ms : [...ms.slice(0, idx), { ...ms[idx], content }];
    });
    void runChat(conv.id, { edit_message_id: messageId, content, model, think });
  };

  const feedback = (messageId: string, value: number) => {
    setMessages((ms) => ms.map((m) => (m.id === messageId ? { ...m, feedback: value || null } : m)));
    void api(`/api/messages/${messageId}`, { method: "PATCH", json: { feedback: value } }).catch((e) =>
      setError(errorMessage(e)),
    );
  };

  const branch = async (messageId: string) => {
    if (!conv) return;
    try {
      const created = await api<Conversation>(`/api/conversations/${conv.id}/branch`, {
        method: "POST",
        json: { message_id: messageId },
      });
      await refreshConversations();
      router.push(`/c/${created.id}`);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const pickMode = (m: Mode) => {
    setMode(m);
    if (conv) void api(`/api/conversations/${conv.id}`, { method: "PATCH", json: { mode: m } }).catch(() => {});
    composer.current?.focus();
  };

  const pickModel = (id: string) => {
    setModel(id);
    if (conv) void api(`/api/conversations/${conv.id}`, { method: "PATCH", json: { model: id } }).catch(() => {});
  };

  // ---------------------------------------------------------------- render
  const display: DisplayMessage[] = [...messages];
  if (streaming) {
    display.push({
      id: `live-${streamToken.current}`,
      role: "assistant",
      content: streaming.content,
      reasoning: streaming.reasoning || null,
      status: "ok",
      feedback: null,
      attachments: [],
      sources: [],
      tool: null,
      streaming: true,
    });
  }
  const isHome = !routeId && messages.length === 0;
  const projectId = conv?.project_id ?? newChatProject;
  const project = projects.find((p) => p.id === projectId);
  const projectChip = project && (
    <Link
      href={`/projetos/${project.id}`}
      className="mx-auto inline-flex items-center gap-1.5 rounded-lg border border-line bg-panel px-3 py-1 text-xs text-muted hover:text-fg"
    >
      <FolderOpen className="size-3.5" /> {routeId ? "Projeto" : "Nova conversa no projeto"}: {project.name}
    </Link>
  );
  const lastAssistant = [...display].reverse().find((m) => m.role === "assistant");

  const composerEl = (
    <Composer
      ref={composer}
      onSend={(t, files) => void send(t, files)}
      onStop={stop}
      streaming={!!streaming}
      think={think}
      onThink={setThink}
      webSearch={webSearch}
      onWebSearch={setWebSearch}
      toolsOn={toolsOn}
      onTools={setToolsOn}
      mode={mode}
      onClearMode={() => pickMode("conversar")}
      models={models}
      model={model}
      onModel={pickModel}
      conversationId={conv?.id ?? null}
      compact={!isHome}
    />
  );

  const errorBanner = error && (
    <div role="alert" className="mx-auto mb-3 flex w-full max-w-3xl items-start gap-2 rounded-xl border border-bad/40 bg-bad/10 px-4 py-2.5 text-sm">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-bad" />
      <span className="flex-1">{error}</span>
      <button type="button" onClick={() => setError(null)} aria-label="Fechar aviso">
        <X className="size-4" />
      </button>
    </div>
  );

  if (isHome) {
    return (
      <div className="vx-scroll h-full overflow-y-auto">
        <div className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-6 sm:px-6">
          <Hero />
          {projectChip}
          <ActionCards active={mode} onPick={pickMode} />
          <SuggestionChips
            onPick={(text, m) => {
              setMode(m);
              composer.current?.setText(text);
              if (/arquivo|PDF/i.test(text)) composer.current?.pickFiles();
            }}
          />
          {errorBanner}
          {composerEl}
          <ShowcaseCards />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scroller} onScroll={onScroll} className="vx-scroll flex-1 overflow-y-auto">
        <RunContext.Provider value={{ canRun, conversationId: conv?.id ?? null }}>
        <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6" aria-live="polite">
          {conv && <h1 className="sr-only">{conv.title}</h1>}
          {projectChip}
          {loading && messages.length === 0 && <p className="text-center text-sm text-subtle">Carregando conversa…</p>}
          {display.map((m) => (
              <MessageView
                key={liveKeys.current.get(m.id) ?? m.id}
                message={m}
                isLast={m === lastAssistant}
                actions={{
                  onRegenerate: regenerate,
                  onEdit: edit,
                  onFeedback: feedback,
                  onBranch: (id) => void branch(id),
                  busy: !!streaming,
                }}
              />
            ))}
        </div>
        </RunContext.Provider>
      </div>
      <motion.div layout className="mx-auto w-full max-w-3xl px-4 pb-4 sm:px-6">
        {errorBanner}
        {memoryNote && (
          <div role="status" className="mx-auto mb-3 flex w-full items-center gap-2 rounded-xl border border-accent-2/40 bg-accent-2/10 px-4 py-2 text-sm">
            <Brain className="size-4 shrink-0 text-accent-2" />
            <span className="flex-1">
              Guardei na memória: <strong>{memoryNote}</strong>{" "}
              <Link href="/memoria" className="text-accent underline">
                ver memória
              </Link>
            </span>
            <button type="button" onClick={() => setMemoryNote(null)} aria-label="Fechar aviso">
              <X className="size-4" />
            </button>
          </div>
        )}
        {composerEl}
        <p className="mt-2 text-center text-[11px] text-subtle">
          O Vortex roda no seu servidor e pode cometer erros. Confira informações importantes.
        </p>
      </motion.div>
    </div>
  );
}
