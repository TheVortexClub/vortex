"use client";

import { AlertCircle, ImagePlus, Video, Wand2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { JobView } from "@/components/chat/job-view";
import { Button, Field, inputClass, PageHeader } from "@/components/ui";
import { useWorkspace } from "@/components/workspace";
import { api, errorMessage, type Job } from "@/lib/api";

const SIZES = [
  { label: "Quadrado 512×512", width: 512, height: 512 },
  { label: "Paisagem 768×512", width: 768, height: 512 },
  { label: "Retrato 512×768", width: 512, height: 768 },
];

export default function CreatePage() {
  const { tools } = useWorkspace();
  const imageTool = tools.find((t) => t.id === "image_generation");
  const videoTool = tools.find((t) => t.id === "video_generation");
  const [prompt, setPrompt] = useState("");
  const [size, setSize] = useState(0);
  const [steps, setSteps] = useState(20);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const res = await api<{ data: Job[] }>("/api/jobs?kind=image&limit=24");
    setJobs(res.data);
  }, []);

  useEffect(() => {
    void load().catch(() => {});
  }, [load]);

  const ready = !!imageTool?.available && imageTool.enabled;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const job = await api<Job>("/api/images", {
        method: "POST",
        json: { prompt, width: SIZES[size].width, height: SIZES[size].height, steps },
      });
      setJobs((js) => [job, ...js]);
      setPrompt("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="vx-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <PageHeader title="Criar" description="Imagens geradas no seu servidor, sem enviar nada para fora." />

        {imageTool && !ready && (
          <div role="status" className="vx-panel mb-6 flex items-start gap-3 p-4 text-sm">
            <AlertCircle className="mt-0.5 size-5 shrink-0 text-warn" />
            <div>
              <p className="font-medium">A geração de imagens ainda não está ativa neste servidor.</p>
              <p className="mt-1 text-muted">{imageTool.enabled ? imageTool.reason : "Ela está desligada nas suas configurações."}</p>
              <Link href="/ferramentas" className="mt-2 inline-block text-accent underline">
                Como ativar
              </Link>
            </div>
          </div>
        )}

        <form onSubmit={submit} className="vx-panel space-y-4 p-5">
          <Field label="Descreva a imagem" hint="Detalhes ajudam: estilo, luz, cores, enquadramento. Em inglês costuma sair melhor.">
            <textarea
              className={`${inputClass} min-h-24`}
              required
              minLength={3}
              maxLength={1000}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ex.: Rio de Janeiro ao pôr do sol visto do Pão de Açúcar, fotografia realista, luz dourada"
            />
          </Field>
          <div className="flex flex-wrap items-end gap-4">
            <Field label="Formato">
              <select className={inputClass} value={size} onChange={(e) => setSize(Number(e.target.value))}>
                {SIZES.map((s, i) => (
                  <option key={s.label} value={i}>
                    {s.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={`Qualidade: ${steps} passos`} hint="Mais passos = melhor e mais lento.">
              <input
                type="range"
                min={8}
                max={40}
                value={steps}
                onChange={(e) => setSteps(Number(e.target.value))}
                className="w-48 accent-[var(--accent)]"
                aria-label="Passos"
              />
            </Field>
            <Button type="submit" disabled={!ready || busy || prompt.trim().length < 3} className="ml-auto">
              <Wand2 className="size-4" /> Gerar imagem
            </Button>
          </div>
          {error && (
            <p role="alert" className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm">
              {error}
            </p>
          )}
        </form>

        <div className="mt-4 flex items-center gap-2 rounded-xl border border-dashed border-line-strong p-4 text-sm text-muted">
          <Video className="size-5 shrink-0" />
          Vídeos com IA: {videoTool?.reason ?? "chegam na etapa 8 do roadmap."}
        </div>

        <h2 className="mb-3 mt-8 text-lg font-semibold">Suas criações</h2>
        {jobs.length === 0 && (
          <p className="flex items-center gap-2 text-sm text-subtle">
            <ImagePlus className="size-4" /> Nada criado ainda.
          </p>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          {jobs.map((j) => (
            <div key={j.id} className="vx-panel p-3">
              <p className="line-clamp-2 text-sm">{j.prompt}</p>
              <JobView jobId={j.id} initial={j} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
