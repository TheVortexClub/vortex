"use client";

import { Command } from "cmdk";
import { BarChart3, FolderOpen, MessageSquareText, Moon, Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Conversation } from "@/lib/api";
import { SECTIONS } from "@/lib/sections";
import { useTheme } from "./theme";
import { useWorkspace } from "./workspace";

const itemClass =
  "flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted data-[selected=true]:bg-chip data-[selected=true]:text-fg";

export function CommandPalette() {
  const { paletteOpen, setPaletteOpen, conversations, projects } = useWorkspace();
  const { toggle } = useTheme();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Conversation[] | null>(null);

  // Server-side search through titles and message text.
  useEffect(() => {
    if (!query.trim()) {
      setResults(null);
      return;
    }
    const timer = setTimeout(() => {
      api<{ data: Conversation[] }>(`/api/conversations?q=${encodeURIComponent(query.trim())}&limit=20`)
        .then((res) => setResults(res.data))
        .catch(() => setResults([]));
    }, 180);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (!paletteOpen) setQuery("");
  }, [paletteOpen]);

  const go = (href: string) => {
    setPaletteOpen(false);
    router.push(href);
  };

  const q = query.trim().toLowerCase();
  const sections = [
    ...SECTIONS,
    { slug: "uso", label: "Uso e desempenho", href: "/uso", icon: BarChart3 },
  ].filter((s) => !q || s.label.toLowerCase().includes(q));
  const matchingProjects = projects.filter((p) => !q || p.name.toLowerCase().includes(q)).slice(0, 6);
  const chats = results ?? conversations.slice(0, 8);

  return (
    <Command.Dialog
      open={paletteOpen}
      onOpenChange={setPaletteOpen}
      label="Pesquisar no Vortex"
      shouldFilter={false}
      overlayClassName="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
      contentClassName="vx-panel fixed left-1/2 top-[12vh] z-50 w-[min(640px,calc(100vw-24px))] -translate-x-1/2 overflow-hidden shadow-2xl"
    >
      <div className="flex items-center gap-3 border-b border-line px-4">
        <Search className="size-4 text-subtle" />
        <Command.Input
          value={query}
          onValueChange={setQuery}
          placeholder="Pesquise conversas, ferramentas, seções..."
          className="h-14 flex-1 bg-transparent text-[15px] outline-none placeholder:text-subtle"
        />
        <kbd className="rounded-md border border-line px-1.5 py-0.5 text-xs text-subtle">Esc</kbd>
      </div>
      <Command.List className="vx-scroll max-h-[60vh] overflow-y-auto p-2">
        <Command.Empty className="px-3 py-6 text-center text-sm text-subtle">
          Nada encontrado.
        </Command.Empty>
        {!q && (
          <Command.Group heading="Ações" className="px-1 pb-2 text-xs text-subtle [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
            <Command.Item value="nova conversa" onSelect={() => go("/")} className={itemClass}>
              <Plus className="size-4" /> Nova conversa
            </Command.Item>
            <Command.Item
              value="alternar tema"
              onSelect={() => {
                toggle();
                setPaletteOpen(false);
              }}
              className={itemClass}
            >
              <Moon className="size-4" /> Alternar tema claro/escuro
            </Command.Item>
          </Command.Group>
        )}
        {chats.length > 0 && (
          <Command.Group heading={q ? "Conversas encontradas" : "Conversas recentes"} className="px-1 pb-2 text-xs text-subtle [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
            {chats.map((c) => (
              <Command.Item key={c.id} value={`chat-${c.id}`} onSelect={() => go(`/c/${c.id}`)} className={itemClass}>
                <MessageSquareText className="size-4 shrink-0" />
                <span className="truncate">{c.title}</span>
              </Command.Item>
            ))}
          </Command.Group>
        )}
        {matchingProjects.length > 0 && (
          <Command.Group heading="Projetos" className="px-1 pb-2 text-xs text-subtle [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
            {matchingProjects.map((p) => (
              <Command.Item key={p.id} value={`project-${p.id}`} onSelect={() => go(`/projetos/${p.id}`)} className={itemClass}>
                <FolderOpen className="size-4 shrink-0" />
                <span className="truncate">{p.name}</span>
              </Command.Item>
            ))}
          </Command.Group>
        )}
        {sections.length > 0 && (
          <Command.Group heading="Seções" className="px-1 text-xs text-subtle [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
            {sections.map(({ slug, label, href, icon: Icon }) => (
              <Command.Item key={slug} value={`section-${slug}`} onSelect={() => go(href)} className={itemClass}>
                <Icon className="size-4" /> {label}
              </Command.Item>
            ))}
          </Command.Group>
        )}
      </Command.List>
    </Command.Dialog>
  );
}
