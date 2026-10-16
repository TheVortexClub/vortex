"use client";

import { BarChart3, Bot, Code2, FileText, Globe, Image as ImageIcon, type LucideIcon, RefreshCw, ScanText, Video, Workflow } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, PageHeader } from "@/components/ui";
import { useWorkspace } from "@/components/workspace";

const ICONS: Record<string, LucideIcon> = {
  web_search: Globe,
  image_generation: ImageIcon,
  video_generation: Video,
  file_analysis: FileText,
  ocr: ScanText,
  data: BarChart3,
  code: Code2,
  agents: Bot,
  automations: Workflow,
};

const HOW: Record<string, string> = {
  web_search: 'No chat, ligue "Pesquisar" antes de enviar. O Vortex pesquisa, lê as páginas e cita as fontes.',
  image_generation: 'No chat, ligue "Ferramentas" e peça "crie uma imagem de…", ou use a página Criar.',
  file_analysis: "Anexe arquivos no + do chat ou envie para um projeto.",
  ocr: "Imagens e PDFs escaneados são lidos automaticamente ao anexar.",
  data: 'Anexe uma planilha/CSV, ligue "Ferramentas" e peça uma análise ou gráfico; clique em Executar no código.',
  code: 'Com "Ferramentas" ligado, blocos de Python nas respostas ganham o botão Executar.',
};

export default function ToolsPage() {
  const { tools, refreshTools } = useWorkspace();
  const [refreshing, setRefreshing] = useState(false);
  const missing = tools.filter((t) => !t.available && t.step <= 6);

  return (
    <div className="vx-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <PageHeader
          title="Ferramentas"
          description="O que o Vortex consegue usar neste servidor. Tudo roda localmente."
          action={
            <Button
              variant="ghost"
              onClick={async () => {
                setRefreshing(true);
                await refreshTools();
                setRefreshing(false);
              }}
            >
              <RefreshCw className={`size-4 ${refreshing ? "animate-spin" : ""}`} /> Verificar de novo
            </Button>
          }
        />
        <div className="grid gap-3 sm:grid-cols-2">
          {tools.map((t) => {
            const Icon = ICONS[t.id] ?? Code2;
            const state = !t.available ? "off" : t.enabled ? "on" : "disabled";
            return (
              <div key={t.id} className="vx-panel flex gap-3 p-4">
                <span className="grid size-11 shrink-0 place-items-center rounded-xl border border-line bg-elev">
                  <Icon className="size-5 text-accent" />
                </span>
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 font-medium">
                    {t.label}
                    <span
                      className={`rounded-md px-2 py-0.5 text-[11px] ${
                        state === "on"
                          ? "bg-ok/15 text-ok"
                          : state === "disabled"
                            ? "bg-chip text-subtle"
                            : "bg-warn/15 text-warn"
                      }`}
                    >
                      {state === "on" ? "pronta" : state === "disabled" ? "desligada por você" : "indisponível"}
                    </span>
                  </p>
                  <p className="mt-1 text-sm text-muted">{t.description}</p>
                  <p className="mt-2 text-xs text-subtle">{t.available ? HOW[t.id] ?? "" : t.reason}</p>
                </div>
              </div>
            );
          })}
        </div>

        {missing.length > 0 && (
          <section className="vx-panel mt-6 p-5 text-sm">
            <h2 className="font-medium">Como ativar o que falta</h2>
            <p className="mt-1 text-muted">
              Quem administra o servidor roda uma vez, na pasta do Vortex:
            </p>
            <pre className="mt-3 overflow-x-auto rounded-xl bg-[var(--code-bg)] p-4 text-[13px] text-slate-100">
              {".\\scripts\\setup-tools.ps1"}
            </pre>
            <p className="mt-3 text-muted">
              Ele liga a pesquisa (SearXNG) e o ambiente isolado de código no Docker. A geração de imagens precisa do
              ComfyUI com um modelo Stable Diffusion; veja o guia em{" "}
              <Link href="https://github.com/TheVortexClub/vortex/blob/main/docs/ferramentas.md" className="text-accent underline" target="_blank">
                docs/ferramentas.md
              </Link>
              .
            </p>
          </section>
        )}
      </div>
    </div>
  );
}
