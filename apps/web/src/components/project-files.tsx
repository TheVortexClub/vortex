"use client";

import { AlertCircle, Download, FileText, Loader2, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ACCEPTED_FILES, api, errorMessage, type FileInfo, formatSize, uploadFile } from "@/lib/api";
import { Button } from "./ui";

/** Files that every conversation of the project can consult. */
export function ProjectFiles({ projectId }: { projectId: string }) {
  const [files, setFiles] = useState<FileInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(0);
  const picker = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const res = await api<{ data: FileInfo[] }>(`/api/files?project_id=${projectId}`);
    setFiles(res.data);
    return res.data;
  }, [projectId]);

  useEffect(() => {
    void load().catch((e) => setError(errorMessage(e)));
  }, [load]);

  // keep refreshing while something is still being read
  useEffect(() => {
    if (!files?.some((f) => f.status === "processing")) return;
    const timer = setInterval(() => void load(), 1200);
    return () => clearInterval(timer);
  }, [files, load]);

  const add = async (list: File[]) => {
    setError(null);
    setUploading((n) => n + list.length);
    await Promise.all(
      list.map((file) =>
        uploadFile(file, { project_id: projectId })
          .catch((e) => setError(`${file.name}: ${errorMessage(e)}`))
          .finally(() => setUploading((n) => n - 1)),
      ),
    );
    await load();
  };

  const remove = async (f: FileInfo) => {
    if (!window.confirm(`Apagar "${f.name}"?`)) return;
    await api(`/api/files/${f.id}`, { method: "DELETE" });
    await load();
  };

  return (
    <section className="mt-8" aria-label="Arquivos do projeto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Arquivos</h2>
          <p className="text-sm text-muted">O Vortex consulta estes arquivos em todas as conversas do projeto.</p>
        </div>
        <Button variant="ghost" onClick={() => picker.current?.click()}>
          {uploading > 0 ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />} Enviar arquivos
        </Button>
        <input
          ref={picker}
          type="file"
          multiple
          hidden
          accept={ACCEPTED_FILES}
          onChange={(e) => {
            void add(Array.from(e.target.files ?? []));
            e.target.value = "";
          }}
        />
      </div>
      {error && (
        <p role="alert" className="mt-3 rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm">
          {error}
        </p>
      )}
      <div
        className="mt-3 space-y-2"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (e.dataTransfer.files.length) void add(Array.from(e.dataTransfer.files));
        }}
      >
        {files?.length === 0 && (
          <p className="rounded-xl border border-dashed border-line-strong p-6 text-center text-sm text-muted">
            Arraste arquivos para cá ou use Enviar arquivos. PDF, Word, planilhas, CSV, código e imagens.
          </p>
        )}
        {files?.map((f) => (
          <div key={f.id} className="flex items-center gap-3 rounded-xl border border-line bg-panel px-4 py-3">
            {f.status === "processing" ? (
              <Loader2 className="size-5 shrink-0 animate-spin text-accent" />
            ) : f.status === "error" ? (
              <AlertCircle className="size-5 shrink-0 text-bad" />
            ) : (
              <FileText className="size-5 shrink-0 text-accent" />
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm">{f.name}</p>
              <p className="text-xs text-subtle">
                {f.status === "processing"
                  ? "lendo o conteúdo…"
                  : f.status === "error"
                    ? f.error
                    : [
                        formatSize(f.size),
                        f.pages ? `${f.pages} ${f.pages === 1 ? "página" : "páginas"}` : null,
                        f.ocr ? "texto lido com OCR" : null,
                        f.embedded ? "busca por significado" : "busca por palavras",
                      ]
                        .filter(Boolean)
                        .join(" • ")}
              </p>
            </div>
            <a
              href={`/api/files/${f.id}/content`}
              className="rounded-lg p-2 text-muted hover:bg-chip hover:text-fg"
              aria-label={`Baixar ${f.name}`}
            >
              <Download className="size-4" />
            </a>
            <button
              type="button"
              onClick={() => void remove(f)}
              className="rounded-lg p-2 text-muted hover:bg-chip hover:text-bad"
              aria-label={`Apagar ${f.name}`}
            >
              <Trash2 className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
