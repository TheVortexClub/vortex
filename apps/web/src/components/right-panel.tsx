"use client";

import {
  Bot,
  Code2,
  FileText,
  Globe,
  Image as ImageIcon,
  type LucideIcon,
  BarChart3,
  ScanText,
  SlidersHorizontal,
  Sparkles,
  Video,
  Workflow,
  Coins,
  Cpu,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { VortexMark } from "./brand";
import { useWorkspace } from "./workspace";

const TOOLS: { label: string; icon: LucideIcon; color: string }[] = [
  { label: "Navegação Web", icon: Globe, color: "text-sky-400" },
  { label: "Geração de Imagens", icon: ImageIcon, color: "text-amber-400" },
  { label: "Geração de Vídeos", icon: Video, color: "text-blue-400" },
  { label: "Análise de Arquivos", icon: FileText, color: "text-indigo-400" },
  { label: "OCR e Texto", icon: ScanText, color: "text-teal-300" },
  { label: "Dados e Planilhas", icon: BarChart3, color: "text-emerald-400" },
  { label: "Programação", icon: Code2, color: "text-cyan-300" },
  { label: "Agentes IA", icon: Bot, color: "text-sky-300" },
  { label: "Automatizações", icon: Workflow, color: "text-violet-400" },
];

function PanelCard({
  title,
  action,
  children,
}: {
  title: string;
  action?: { label: string; href: string };
  children: React.ReactNode;
}) {
  return (
    <section className="vx-panel p-4" aria-label={title}>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[15px] font-medium">{title}</h2>
        {action && (
          <Link href={action.href} className="text-sm text-accent hover:underline">
            {action.label}
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

function Ring({ percent }: { percent: number }) {
  const r = 30;
  const c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 80 80" className="size-20 shrink-0" role="img" aria-label={`${percent}% disponível`}>
      <defs>
        <linearGradient id="vx-ring" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#34d399" />
          <stop offset="1" stopColor="#22d3ee" />
        </linearGradient>
      </defs>
      <circle cx="40" cy="40" r={r} fill="none" stroke="var(--border)" strokeWidth="7" />
      <circle
        cx="40"
        cy="40"
        r={r}
        fill="none"
        stroke="url(#vx-ring)"
        strokeWidth="7"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - percent / 100)}
        transform="rotate(-90 40 40)"
        style={{ filter: "drop-shadow(0 0 6px rgb(52 211 153 / 0.5))" }}
      />
      <text x="40" y="45" textAnchor="middle" className="fill-fg text-[15px] font-semibold">
        {percent}%
      </text>
    </svg>
  );
}

export function RightPanel() {
  const { defaultModel, usage } = useWorkspace();
  const fmt = (n: number) => n.toLocaleString("pt-BR");

  return (
    <aside className="vx-scroll hidden w-[330px] shrink-0 space-y-4 overflow-y-auto py-5 pr-5 xl:block" aria-label="Painel">
      <PanelCard title="Modelo Ativo">
        <div className="flex items-start gap-3">
          <span className="grid size-14 shrink-0 place-items-center rounded-xl border border-line-strong bg-elev">
            <VortexMark className="size-10" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{defaultModel?.display_name ?? "Vortex v0.2.1"}</span>
              {(defaultModel?.badge ?? "PRÓPRIO") && (
                <span className="vx-badge rounded-md px-2 py-0.5 text-[11px] font-medium">
                  {defaultModel?.badge ?? "PRÓPRIO"}
                </span>
              )}
            </p>
            <p className="mt-1 text-sm text-muted">
              {defaultModel?.description ?? "Nosso modelo exclusivo. Rápido, inteligente e versátil."}
            </p>
          </div>
          <Link
            href="/configuracoes"
            className="grid size-9 shrink-0 place-items-center rounded-lg border border-line text-muted hover:text-fg"
            aria-label="Configurações do modelo"
          >
            <SlidersHorizontal className="size-4" />
          </Link>
        </div>
      </PanelCard>

      <PanelCard title="Ferramentas" action={{ label: "Ver todas", href: "/ferramentas" }}>
        <div className="grid grid-cols-3 gap-2">
          {TOOLS.map(({ label, icon: Icon, color }) => (
            <Link
              key={label}
              href="/ferramentas"
              title={`${label} — em breve`}
              className="flex h-[84px] flex-col items-center justify-center gap-2 rounded-xl border border-line bg-elev/60 px-1 text-center text-[11.5px] leading-tight text-muted transition hover:border-line-strong hover:text-fg"
            >
              <Icon className={`size-6 ${color}`} />
              {label}
            </Link>
          ))}
        </div>
      </PanelCard>

      <PanelCard title="Seus Projetos" action={{ label: "Ver todas", href: "/projetos" }}>
        <div className="rounded-xl border border-dashed border-line-strong p-4 text-center text-sm text-muted">
          <Sparkles className="mx-auto mb-2 size-5 text-accent" />
          Nenhum projeto ainda. Projetos para agrupar conversas e arquivos chegam na etapa 4.
        </div>
      </PanelCard>

      <PanelCard title="Uso e Desempenho">
        <div className="flex items-center gap-4 rounded-xl border border-line bg-elev/60 p-3">
          <Ring percent={100} />
          <div className="text-sm">
            <p className="font-medium">{usage?.plan.name ?? "Livre"}</p>
            <p>{usage?.plan.credits ?? "Sem uso de créditos"}</p>
            <p className="text-xs text-muted">Acesso completo ao Vortex v0.2.1</p>
          </div>
        </div>
        {usage && usage.requests > 0 && (
          <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
            <Stat label="Respostas" value={fmt(usage.requests)} />
            <Stat label="Tokens" value={fmt(usage.total_tokens)} />
            <Stat
              label="Tokens/s"
              value={usage.avg_tokens_per_sec != null ? usage.avg_tokens_per_sec.toFixed(1) : "—"}
            />
          </dl>
        )}
        <ul className="mt-3 space-y-1.5 text-sm text-muted">
          <li className="flex items-center gap-2"><Sparkles className="size-4" /> Sem plano pago</li>
          <li className="flex items-center gap-2"><Coins className="size-4" /> Sem créditos</li>
          <li className="flex items-center gap-2"><Cpu className="size-4" /> Modelo próprio v0.2.1</li>
          <li className="flex items-center gap-2"><ShieldCheck className="size-4" /> Roda no seu servidor</li>
        </ul>
      </PanelCard>
    </aside>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-elev/60 px-2 py-2">
      <dd className="text-sm font-semibold">{value}</dd>
      <dt className="text-[11px] text-subtle">{label}</dt>
    </div>
  );
}
