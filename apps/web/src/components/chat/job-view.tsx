"use client";

import { AlertCircle, Download, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Job } from "@/lib/api";

/** Follows an image/video job until it finishes, then shows the result. */
export function JobView({ jobId, initial }: { jobId: string; initial?: Job }) {
  const [job, setJob] = useState<Job | null>(initial ?? null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const j = await api<Job>(`/api/jobs/${jobId}`);
        if (stop) return;
        setJob(j);
        if (j.status === "done" || j.status === "error") return;
      } catch {
        // keep trying; the server may be busy
      }
      if (!stop) setTimeout(tick, 2000);
    };
    void tick();
    return () => {
      stop = true;
    };
  }, [jobId]);

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "error") return;
    const started = new Date(job.created_at).getTime();
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [job]);

  if (!job) return null;

  if (job.status === "error") {
    return (
      <p className="mt-3 flex items-center gap-2 rounded-xl border border-bad/40 bg-bad/10 px-3 py-2 text-sm">
        <AlertCircle className="size-4 shrink-0 text-bad" /> {job.error ?? "Não deu para gerar."}
      </p>
    );
  }

  if (job.status !== "done") {
    const pct = Math.round(job.progress * 100);
    const min = Math.floor(elapsed / 60);
    return (
      <div className="mt-3 max-w-sm rounded-xl border border-line bg-elev/60 p-3 text-sm" role="status">
        <p className="flex items-center gap-2 text-muted">
          <Loader2 className="size-4 animate-spin text-accent" />
          {job.status === "queued" ? "Na fila…" : `Gerando ${job.kind === "video" ? "vídeo" : "imagem"}…`}
          <span className="ml-auto tabular-nums text-subtle">
            {min > 0 ? `${min} min ` : ""}
            {elapsed % 60} s
          </span>
        </p>
        <div
          className="mt-2 h-1.5 overflow-hidden rounded-full bg-line"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Progresso"
        >
          <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${Math.max(pct, 3)}%` }} />
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 flex flex-wrap gap-3">
      {job.files.map((f) => (
        <figure key={f.id} className="group relative overflow-hidden rounded-xl border border-line">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/api/files/${f.id}/content`}
            alt={job.prompt}
            className="max-h-96 w-auto max-w-full"
            loading="lazy"
          />
          <a
            href={`/api/files/${f.id}/content`}
            download={f.name}
            className="absolute right-2 top-2 rounded-lg bg-black/60 p-2 text-white opacity-0 transition group-hover:opacity-100"
            aria-label="Baixar imagem"
          >
            <Download className="size-4" />
          </a>
        </figure>
      ))}
    </div>
  );
}
