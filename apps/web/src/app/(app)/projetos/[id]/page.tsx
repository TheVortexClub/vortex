"use client";

import { ArrowLeft, FolderOpen, MessageSquarePlus, MessageSquareText, Pencil, Pin, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ProjectFiles } from "@/components/project-files";
import { ProjectForm } from "@/components/project-form";
import { Button, PROJECT_COLORS } from "@/components/ui";
import { useWorkspace } from "@/components/workspace";
import { api, ApiError, type Conversation, errorMessage, type Project } from "@/lib/api";
import { timeAgo } from "@/lib/text";

type ProjectDetail = Project & { conversations: Conversation[] };

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { refreshProjects, refreshConversations } = useWorkspace();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const load = useCallback(async () => {
    try {
      setProject(await api<ProjectDetail>(`/api/projects/${id}`));
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) router.replace("/projetos");
      else setError(errorMessage(e));
    }
  }, [id, router]);

  useEffect(() => {
    void load();
  }, [load]);

  const remove = async () => {
    if (!project) return;
    if (!window.confirm(`Apagar o projeto "${project.name}"? As conversas continuam existindo, fora do projeto.`)) return;
    await api(`/api/projects/${project.id}`, { method: "DELETE" });
    await Promise.all([refreshProjects(), refreshConversations()]);
    router.push("/projetos");
  };

  if (error) return <p className="p-8 text-bad">{error}</p>;
  if (!project) return <p className="p-8 text-subtle">Carregando projeto…</p>;
  const color = PROJECT_COLORS[project.color];

  return (
    <div className="vx-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <Link href="/projetos" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg">
          <ArrowLeft className="size-4" /> Projetos
        </Link>
        <div className="flex flex-wrap items-start gap-4">
          <span className={`grid size-14 place-items-center rounded-2xl ${color.bg}`}>
            <FolderOpen className={`size-7 ${color.fg}`} />
          </span>
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-semibold">{project.name}</h1>
            {project.description && <p className="mt-1 text-muted">{project.description}</p>}
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setEditing(true)}>
              <Pencil className="size-4" /> Editar
            </Button>
            <Button variant="danger" onClick={() => void remove()} aria-label="Apagar projeto">
              <Trash2 className="size-4" />
            </Button>
          </div>
        </div>

        <section className="vx-panel mt-6 p-4">
          <h2 className="text-sm font-medium text-muted">Instruções do projeto</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm">
            {project.instructions || (
              <span className="text-subtle">
                Nenhuma ainda. Adicione contexto (objetivo, tom, regras) em Editar e o Vortex vai considerar em todas as
                conversas deste projeto.
              </span>
            )}
          </p>
        </section>

        <div className="mt-8 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Conversas</h2>
          <Link
            href={`/?projeto=${project.id}`}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-white hover:brightness-110"
          >
            <MessageSquarePlus className="size-4" /> Nova conversa no projeto
          </Link>
        </div>
        <div className="mt-3 space-y-2">
          {project.conversations.length === 0 && (
            <p className="rounded-xl border border-dashed border-line-strong p-6 text-center text-sm text-muted">
              Nenhuma conversa neste projeto ainda.
            </p>
          )}
          {project.conversations.map((c) => (
            <Link
              key={c.id}
              href={`/c/${c.id}`}
              className="flex items-center gap-3 rounded-xl border border-line bg-panel px-4 py-3 hover:border-line-strong"
            >
              <MessageSquareText className="size-4 text-subtle" />
              <span className="flex-1 truncate">{c.title}</span>
              {c.pinned && <Pin className="size-3.5 text-accent" aria-label="Fixada" />}
              <span className="text-xs text-subtle">{timeAgo(c.updated_at)}</span>
            </Link>
          ))}
        </div>

        <ProjectFiles projectId={project.id} />
      </div>
      {editing && (
        <ProjectForm
          open
          project={project}
          onClose={() => setEditing(false)}
          onSaved={() => {
            void load();
            void refreshProjects();
          }}
        />
      )}
    </div>
  );
}
