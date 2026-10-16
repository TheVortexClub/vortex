"use client";

import { Cpu, Gauge, MemoryStick, MonitorCog, Timer, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { useSession } from "@/components/session";
import { PageHeader } from "@/components/ui";
import { api, type SystemStats, type Usage, type UsageHistory } from "@/lib/api";

type Scope = "me" | "server";
const nf = (n: number) => n.toLocaleString("pt-BR");

export default function UsagePage() {
  const { state } = useSession();
  const isAdmin = state.status === "ready" && state.me.user.is_admin;
  const [scope, setScope] = useState<Scope>("me");
  const [days, setDays] = useState(14);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [history, setHistory] = useState<UsageHistory | null>(null);
  const [system, setSystem] = useState<SystemStats | null>(null);

  useEffect(() => {
    api<Usage>(`/api/usage?scope=${scope}`).then(setUsage).catch(() => {});
    api<UsageHistory>(`/api/usage/history?scope=${scope}&days=${days}`).then(setHistory).catch(() => {});
  }, [scope, days]);

  useEffect(() => {
    const load = () => api<SystemStats>("/api/system").then(setSystem).catch(() => {});
    void load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="vx-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <PageHeader
          title="Uso e Desempenho"
          description="Plano Livre: sem créditos, sem limites de uso. Tudo roda no seu servidor."
          action={
            <div className="flex gap-2" role="group" aria-label="Filtros">
              {isAdmin && (
                <select
                  value={scope}
                  onChange={(e) => setScope(e.target.value as Scope)}
                  aria-label="De quem"
                  className="h-10 rounded-xl border border-line bg-elev px-3 text-sm"
                >
                  <option value="me">Meu uso</option>
                  <option value="server">Servidor inteiro</option>
                </select>
              )}
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                aria-label="Período"
                className="h-10 rounded-xl border border-line bg-elev px-3 text-sm"
              >
                <option value={7}>Últimos 7 dias</option>
                <option value={14}>Últimos 14 dias</option>
                <option value={30}>Últimos 30 dias</option>
              </select>
            </div>
          }
        />

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Tile icon={Zap} label="Respostas" value={usage ? nf(usage.requests) : "—"} />
          <Tile icon={Gauge} label="Tokens" value={usage ? nf(usage.total_tokens) : "—"} />
          <Tile
            icon={Timer}
            label="Latência média"
            value={usage?.avg_latency_ms != null ? `${(usage.avg_latency_ms / 1000).toFixed(1)} s` : "—"}
            hint={usage?.avg_ttft_ms != null ? `1º token em ${(usage.avg_ttft_ms / 1000).toFixed(1)} s` : undefined}
          />
          <Tile
            icon={Cpu}
            label="Velocidade"
            value={usage?.avg_tokens_per_sec != null ? `${usage.avg_tokens_per_sec.toFixed(1)} tok/s` : "—"}
          />
        </div>

        <section className="vx-panel mt-4 p-5">
          <h2 className="font-medium">Respostas por dia</h2>
          {history && <DailyBars days={history.days} />}
        </section>

        <section className="vx-panel mt-4 overflow-x-auto p-5">
          <h2 className="mb-3 font-medium">Por modelo</h2>
          {history && history.models.length === 0 && <p className="text-sm text-subtle">Sem uso no período.</p>}
          {history && history.models.length > 0 && (
            <table className="w-full text-sm">
              <thead className="text-left text-subtle">
                <tr>
                  <th className="pb-2 font-normal">Modelo</th>
                  <th className="pb-2 text-right font-normal">Respostas</th>
                  <th className="pb-2 text-right font-normal">Tokens</th>
                  <th className="pb-2 text-right font-normal">Latência</th>
                  <th className="pb-2 text-right font-normal">tok/s</th>
                </tr>
              </thead>
              <tbody>
                {history.models.map((m) => (
                  <tr key={m.model} className="border-t border-line">
                    <td className="py-2">{m.model}</td>
                    <td className="py-2 text-right tabular-nums">{nf(m.requests)}</td>
                    <td className="py-2 text-right tabular-nums">{nf(m.tokens)}</td>
                    <td className="py-2 text-right tabular-nums">
                      {m.avg_latency_ms != null ? `${(m.avg_latency_ms / 1000).toFixed(1)} s` : "—"}
                    </td>
                    <td className="py-2 text-right tabular-nums">{m.avg_tokens_per_sec?.toFixed(1) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="vx-panel mt-4 p-5" aria-live="polite">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-medium">Servidor agora</h2>
            <span className="text-xs text-subtle">{system?.platform} • atualiza a cada 5 s</span>
          </div>
          {system && (
            <div className="grid gap-4 md:grid-cols-3">
              <Meter icon={Cpu} label={`CPU (${system.cpu.cores} núcleos)`} percent={system.cpu.percent} detail={system.cpu.name} />
              <Meter
                icon={MemoryStick}
                label="Memória RAM"
                percent={system.memory.percent}
                detail={`${system.memory.used_gb} de ${system.memory.total_gb} GB`}
              />
              <div>
                <p className="flex items-center gap-2 text-sm text-muted">
                  <MonitorCog className="size-4" /> GPU
                </p>
                {system.gpus.length === 0 && <p className="mt-2 text-sm">Nenhuma detectada</p>}
                {system.gpus.map((g) => (
                  <p key={g.name} className="mt-2 text-sm">
                    {g.name}
                    <span className="block text-xs text-subtle">
                      {g.utilization != null
                        ? `${g.utilization}% em uso • ${Math.round(g.memory_used_mb ?? 0)}/${Math.round(g.memory_total_mb ?? 0)} MB`
                        : "Sem CUDA: o modelo roda na CPU"}
                    </span>
                  </p>
                ))}
              </div>
            </div>
          )}
          {system?.loaded_models && (
            <div className="mt-5 border-t border-line pt-4 text-sm">
              <p className="text-muted">Modelos carregados agora</p>
              {system.loaded_models.length === 0 ? (
                <p className="mt-1 text-subtle">Nenhum (o modelo carrega na próxima pergunta).</p>
              ) : (
                <ul className="mt-1 space-y-1">
                  {system.loaded_models.map((m) => (
                    <li key={m.name}>
                      {m.name} <span className="text-subtle">• {m.size_gb} GB • {m.processor}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Tile({ icon: Icon, label, value, hint }: { icon: typeof Cpu; label: string; value: string; hint?: string }) {
  return (
    <div className="vx-panel p-4">
      <p className="flex items-center gap-2 text-sm text-muted">
        <Icon className="size-4" /> {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="text-xs text-subtle">{hint}</p>}
    </div>
  );
}

function Meter({ icon: Icon, label, percent, detail }: { icon: typeof Cpu; label: string; percent: number; detail: string }) {
  return (
    <div>
      <p className="flex items-center justify-between text-sm text-muted">
        <span className="flex items-center gap-2">
          <Icon className="size-4" /> {label}
        </span>
        <span className="tabular-nums text-fg">{Math.round(percent)}%</span>
      </p>
      <div
        className="mt-2 h-2 overflow-hidden rounded-full bg-line"
        role="meter"
        aria-label={label}
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${Math.min(percent, 100)}%` }} />
      </div>
      <p className="mt-1 truncate text-xs text-subtle">{detail}</p>
    </div>
  );
}

/** Single-series bar chart: one hue, 4px rounded tops on the baseline, 2px gaps, hover tooltip. */
function DailyBars({ days }: { days: UsageHistory["days"] }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...days.map((d) => d.requests));
  const label = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  const total = days.reduce((a, d) => a + d.requests, 0);
  return (
    <div className="mt-4">
      {total === 0 && <p className="mb-2 text-sm text-subtle">Sem respostas no período.</p>}
      <div className="relative flex h-44 items-end gap-[2px] border-b border-line" role="img" aria-label={`Respostas por dia, total ${total}`}>
        {days.map((d, i) => (
          <div
            key={d.date}
            className="relative flex h-full flex-1 items-end"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          >
            <div
              className={`w-full rounded-t-[4px] transition-colors ${hover === i ? "bg-accent" : "bg-accent/70"}`}
              style={{ height: d.requests ? `${Math.max(3, (d.requests / max) * 100)}%` : 0 }}
            />
            {hover === i && (
              <div className="vx-panel pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 whitespace-nowrap px-3 py-2 text-xs shadow-xl">
                <p className="font-medium">{label(d.date)}</p>
                <p>{nf(d.requests)} respostas</p>
                <p className="text-muted">{nf(d.tokens)} tokens</p>
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-subtle">
        <span>{label(days[0].date)}</span>
        <span>{label(days[days.length - 1].date)}</span>
      </div>
    </div>
  );
}
