"use client";

import { FolderOpen, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ProjectForm } from "@/components/project-form";
import { Button, PageHeader, PROJECT_COLORS } from "@/components/ui";
import { useWorkspace } from "@/components/workspace";
import { timeAgo } from "@/lib/text";

export default function ProjectsPage() {
  const { projects, projectsLoaded, refreshProjects } = useWorkspace();
  const [creating, setCreating] = useState(false);

  return (
    <div className="vx-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <PageHeader
          title="Projetos"
          description="Reúna conversas com o mesmo contexto. As instruções do projeto valem para todas elas."
          action={
            <Button onClick={() => setCreating(true)}>
              <Plus className="size-4" /> Novo projeto
            </Button>
          }
        />
        {projectsLoaded && projects.length === 0 && (
          <div className="vx-panel p-10 text-center">
            <FolderOpen className="mx-auto size-10 text-accent" />
            <p className="mt-3 font-medium">Nenhum projeto ainda</p>
            <p className="mt-1 text-sm text-muted">
              Crie um projeto para um trabalho, um estudo ou um cliente, e converse com o Vortex dentro dele.
            </p>
            <Button className="mt-5" onClick={() => setCreating(true)}>
              <Plus className="size-4" /> Criar o primeiro projeto
            </Button>
          </div>
        )}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => {
            const color = PROJECT_COLORS[p.color];
            return (
              <Link
                key={p.id}
                href={`/projetos/${p.id}`}
                className="vx-panel group flex flex-col gap-3 p-4 transition hover:-translate-y-0.5 hover:border-line-strong"
              >
                <span className={`grid size-11 place-items-center rounded-xl ${color.bg}`}>
                  <FolderOpen className={`size-5 ${color.fg}`} />
                </span>
                <div className="min-w-0">
                  <p className="truncate font-semibold">{p.name}</p>
                  {p.description && <p className="mt-0.5 line-clamp-2 text-sm text-muted">{p.description}</p>}
                </div>
                <p className="mt-auto text-xs text-subtle">
                  {p.conversation_count} {p.conversation_count === 1 ? "conversa" : "conversas"} • modificado{" "}
                  {timeAgo(p.last_activity)}
                </p>
              </Link>
            );
          })}
        </div>
      </div>
      {creating && (
        <ProjectForm open onClose={() => setCreating(false)} onSaved={() => void refreshProjects()} />
      )}
    </div>
  );
}
