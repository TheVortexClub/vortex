"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";

type ModelInfo = {
  id: string;
  display_name: string;
  badge: string | null;
  description: string;
  kind: string;
};

type Health = {
  status: "ok" | "degraded";
  backends: Record<string, { ok: boolean; detail?: string }>;
};

export function ApiStatus() {
  const [models, setModels] = useState<ModelInfo[] | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/api/models`).then((r) => r.json()),
      fetch(`${API_URL}/api/health`).then((r) => r.json()),
    ])
      .then(([m, h]) => {
        setModels(m.data);
        setHealth(h);
      })
      .catch(() => setError(`API indisponível em ${API_URL}`));
  }, []);

  if (error) {
    return <p className="rounded-xl border border-red-500/40 px-4 py-2 text-red-300">{error}</p>;
  }
  if (!models || !health) {
    return <p className="text-vx-muted">Conectando à API…</p>;
  }

  const chat = models.find((m) => m.kind === "chat");
  return (
    <section
      aria-label="Modelo Ativo"
      className="vx-glow w-full max-w-md rounded-2xl bg-vx-surface/80 p-4 text-left"
    >
      <p className="text-sm text-vx-muted">Modelo Ativo</p>
      {chat && (
        <div className="mt-1 flex items-center gap-2">
          <span className="font-semibold">{chat.display_name}</span>
          {chat.badge && (
            <span className="rounded bg-vx-violet/30 px-2 py-0.5 text-xs text-violet-200">
              {chat.badge}
            </span>
          )}
        </div>
      )}
      {chat && <p className="text-sm text-vx-muted">{chat.description}</p>}
      <p className={`mt-2 text-sm ${health.status === "ok" ? "text-emerald-300" : "text-amber-300"}`}>
        {health.status === "ok" ? "● Modelo online" : "● Backend do modelo indisponível"}
      </p>
    </section>
  );
}
