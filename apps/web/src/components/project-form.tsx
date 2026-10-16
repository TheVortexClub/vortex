"use client";

import { useState } from "react";
import { api, errorMessage, type Project, type ProjectColor } from "@/lib/api";
import { Button, Field, inputClass, Modal, PROJECT_COLORS } from "./ui";

type Draft = Pick<Project, "name" | "description" | "instructions" | "color">;

export function ProjectForm({
  open,
  onClose,
  project,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  project?: Project;
  onSaved: (p: Project) => void;
}) {
  const [draft, setDraft] = useState<Draft>({
    name: project?.name ?? "",
    description: project?.description ?? "",
    instructions: project?.instructions ?? "",
    color: project?.color ?? "blue",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = project
        ? await api<Project>(`/api/projects/${project.id}`, { method: "PATCH", json: draft })
        : await api<Project>("/api/projects", { method: "POST", json: draft });
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={project ? "Editar projeto" : "Novo projeto"}>
      <form onSubmit={save} className="space-y-4">
        <Field label="Nome">
          <input
            className={inputClass}
            required
            maxLength={120}
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            placeholder="Ex.: Jogo UE5 - Rio de Janeiro"
          />
        </Field>
        <Field label="Descrição">
          <input
            className={inputClass}
            maxLength={2000}
            value={draft.description}
            onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            placeholder="Para que serve este projeto"
          />
        </Field>
        <Field
          label="Instruções para o Vortex"
          hint="Valem para todas as conversas do projeto: contexto, tom, regras."
        >
          <textarea
            className={`${inputClass} min-h-28`}
            maxLength={8000}
            value={draft.instructions}
            onChange={(e) => setDraft({ ...draft, instructions: e.target.value })}
            placeholder="Ex.: O jogo é em Unreal Engine 5, estilo realista, ambientado no Rio..."
          />
        </Field>
        <fieldset>
          <legend className="mb-2 text-sm font-medium">Cor</legend>
          <div className="flex gap-2">
            {(Object.keys(PROJECT_COLORS) as ProjectColor[]).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setDraft({ ...draft, color: c })}
                aria-label={PROJECT_COLORS[c].label}
                aria-pressed={draft.color === c}
                className={`size-8 rounded-lg ${PROJECT_COLORS[c].bg} ring-2 ${
                  draft.color === c ? "ring-accent" : "ring-transparent"
                }`}
              >
                <span className={`mx-auto block size-3 rounded-full bg-current ${PROJECT_COLORS[c].fg}`} />
              </button>
            ))}
          </div>
        </fieldset>
        {error && (
          <p role="alert" className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={busy}>
            {project ? "Salvar" : "Criar projeto"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
