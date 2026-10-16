"use client";

import { Brain, Check, MessageSquareText, Pencil, Plus, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button, inputClass, PageHeader, Toggle } from "@/components/ui";
import { useWorkspace } from "@/components/workspace";
import { api, errorMessage, type MemoryItem } from "@/lib/api";
import { timeAgo } from "@/lib/text";

export default function MemoryPage() {
  const { refreshSettings } = useWorkspace();
  const [enabled, setEnabled] = useState(true);
  const [items, setItems] = useState<MemoryItem[] | null>(null);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState<{ id: string; text: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await api<{ enabled: boolean; data: MemoryItem[] }>("/api/memory");
    setEnabled(res.enabled);
    setItems(res.data);
  }, []);

  useEffect(() => {
    void load().catch((e) => setError(errorMessage(e)));
  }, [load]);

  const run = async (fn: () => Promise<unknown>) => {
    setError(null);
    try {
      await fn();
      await load();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div className="vx-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <PageHeader
          title="Memória"
          description='Coisas que o Vortex lembra sobre você entre conversas. Para guardar algo no chat, diga "lembre que…".'
        />

        <div className="vx-panel mb-6 flex items-center justify-between gap-4 p-4">
          <div>
            <p className="font-medium">Usar memória</p>
            <p className="text-sm text-muted">
              Desligada, o Vortex não guarda nem usa nada daqui. O que já está guardado continua até você apagar.
            </p>
          </div>
          <Toggle
            label="Usar memória"
            checked={enabled}
            onChange={(v) =>
              void run(async () => {
                await api("/api/settings", { method: "PATCH", json: { memory_enabled: v } });
                await refreshSettings();
              })
            }
          />
        </div>

        <form
          className="mb-6 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!draft.trim()) return;
            void run(async () => {
              await api("/api/memory", { method: "POST", json: { content: draft.trim() } });
              setDraft("");
            });
          }}
        >
          <input
            className={inputClass}
            value={draft}
            maxLength={500}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ex.: Prefiro respostas curtas e com exemplos"
            aria-label="Nova memória"
          />
          <Button type="submit" disabled={!draft.trim()}>
            <Plus className="size-4" /> Adicionar
          </Button>
        </form>

        {error && (
          <p role="alert" className="mb-4 rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm">
            {error}
          </p>
        )}

        {items?.length === 0 && (
          <div className="vx-panel p-10 text-center">
            <Brain className="mx-auto size-10 text-accent-2" />
            <p className="mt-3 font-medium">Nada guardado ainda</p>
            <p className="mt-1 text-sm text-muted">
              No chat, escreva por exemplo &quot;lembre que eu moro em Niterói&quot;.
            </p>
          </div>
        )}

        <ul className="space-y-2">
          {items?.map((m) => (
            <li key={m.id} className="flex items-start gap-3 rounded-xl border border-line bg-panel p-4">
              <Brain className="mt-0.5 size-4 shrink-0 text-accent-2" />
              {editing?.id === m.id ? (
                <form
                  className="flex flex-1 gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void run(async () => {
                      await api(`/api/memory/${m.id}`, { method: "PATCH", json: { content: editing.text } });
                      setEditing(null);
                    });
                  }}
                >
                  <input
                    autoFocus
                    className={inputClass}
                    value={editing.text}
                    maxLength={500}
                    onChange={(e) => setEditing({ id: m.id, text: e.target.value })}
                    aria-label="Editar memória"
                  />
                  <button type="submit" aria-label="Salvar" className="rounded-lg p-2 hover:bg-chip">
                    <Check className="size-4" />
                  </button>
                  <button type="button" aria-label="Cancelar" onClick={() => setEditing(null)} className="rounded-lg p-2 hover:bg-chip">
                    <X className="size-4" />
                  </button>
                </form>
              ) : (
                <>
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px]">{m.content}</p>
                    <p className="mt-1 flex items-center gap-1 text-xs text-subtle">
                      {m.source === "chat" && m.conversation_id ? (
                        <Link href={`/c/${m.conversation_id}`} className="inline-flex items-center gap-1 hover:text-fg">
                          <MessageSquareText className="size-3" /> guardada numa conversa
                        </Link>
                      ) : (
                        "adicionada por você"
                      )}{" "}
                      • {timeAgo(m.updated_at)}
                    </p>
                  </div>
                  <button
                    type="button"
                    aria-label="Editar"
                    onClick={() => setEditing({ id: m.id, text: m.content })}
                    className="rounded-lg p-2 text-muted hover:bg-chip hover:text-fg"
                  >
                    <Pencil className="size-4" />
                  </button>
                  <button
                    type="button"
                    aria-label="Esquecer"
                    onClick={() => void run(() => api(`/api/memory/${m.id}`, { method: "DELETE" }))}
                    className="rounded-lg p-2 text-muted hover:bg-chip hover:text-bad"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>

        {items && items.length > 1 && (
          <div className="mt-6 text-right">
            <Button
              variant="danger"
              onClick={() => {
                if (window.confirm("Esquecer tudo o que está na memória?"))
                  void run(() => api("/api/memory", { method: "DELETE" }));
              }}
            >
              <Trash2 className="size-4" /> Esquecer tudo
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
