"use client";

import {
  ArrowRight,
  Download,
  MoreHorizontal,
  Pencil,
  Pin,
  PinOff,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, type Conversation } from "@/lib/api";
import { SECTIONS } from "@/lib/sections";
import { RioSkyline } from "./rio-skyline";
import { useWorkspace } from "./workspace";

function ConversationItem({ conv, active }: { conv: Conversation; active: boolean }) {
  const { refreshConversations } = useWorkspace();
  const router = useRouter();
  const [menu, setMenu] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState(conv.title);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menu) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setMenu(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menu]);

  const update = async (body: Partial<Conversation>) => {
    await api(`/api/conversations/${conv.id}`, { method: "PATCH", json: body });
    await refreshConversations();
  };

  const remove = async () => {
    setMenu(false);
    if (!window.confirm(`Apagar a conversa "${conv.title}"?`)) return;
    await api(`/api/conversations/${conv.id}`, { method: "DELETE" });
    await refreshConversations();
    if (active) router.push("/");
  };

  if (renaming) {
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setRenaming(false);
          if (title.trim() && title.trim() !== conv.title) void update({ title: title.trim() });
        }}
      >
        <input
          autoFocus
          value={title}
          maxLength={200}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={() => setRenaming(false)}
          onKeyDown={(e) => e.key === "Escape" && setRenaming(false)}
          aria-label="Novo nome da conversa"
          className="w-full rounded-lg border border-accent bg-elev px-3 py-1.5 text-sm outline-none"
        />
      </form>
    );
  }

  return (
    <div ref={ref} className="group relative">
      <Link
        href={`/c/${conv.id}`}
        className={`flex items-center gap-2 rounded-lg px-3 py-1.5 pr-8 text-sm transition ${
          active ? "bg-chip text-fg" : "text-muted hover:bg-chip hover:text-fg"
        }`}
        aria-current={active ? "page" : undefined}
      >
        {conv.pinned && <Pin className="size-3 shrink-0 text-accent" aria-label="Fixada" />}
        <span className="truncate">{conv.title}</span>
      </Link>
      <button
        type="button"
        onClick={() => setMenu((m) => !m)}
        className="absolute right-1 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-md text-subtle opacity-0 hover:bg-elev hover:text-fg focus:opacity-100 group-hover:opacity-100"
        aria-label={`Opções de "${conv.title}"`}
        aria-expanded={menu}
      >
        <MoreHorizontal className="size-4" />
      </button>
      {menu && (
        <div className="vx-panel absolute right-0 top-8 z-30 w-44 p-1 text-sm shadow-2xl" role="menu">
          <MenuButton
            icon={conv.pinned ? PinOff : Pin}
            label={conv.pinned ? "Desafixar" : "Fixar"}
            onClick={() => {
              setMenu(false);
              void update({ pinned: !conv.pinned });
            }}
          />
          <MenuButton
            icon={Pencil}
            label="Renomear"
            onClick={() => {
              setMenu(false);
              setTitle(conv.title);
              setRenaming(true);
            }}
          />
          <MenuButton
            icon={Download}
            label="Exportar (.md)"
            onClick={() => {
              setMenu(false);
              window.location.href = `/api/conversations/${conv.id}/export`;
            }}
          />
          <MenuButton icon={Trash2} label="Apagar" danger onClick={() => void remove()} />
        </div>
      )}
    </div>
  );
}

function MenuButton({
  icon: Icon,
  label,
  onClick,
  danger,
}: {
  icon: typeof Pin;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className={`flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left hover:bg-chip ${
        danger ? "text-bad" : ""
      }`}
    >
      <Icon className="size-4" /> {label}
    </button>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { conversations, conversationsLoaded, sidebarOpen, setSidebarOpen } = useWorkspace();
  const activeConv = pathname.startsWith("/c/") ? pathname.slice(3) : null;

  useEffect(() => setSidebarOpen(false), [pathname, setSidebarOpen]);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" || pathname.startsWith("/c/") : pathname.startsWith(href);

  return (
    <>
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-line bg-bg transition-transform lg:static lg:z-auto lg:w-64 lg:translate-x-0 lg:bg-transparent ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Navegação principal"
      >
        <div className="flex items-center justify-between p-3 lg:hidden">
          <span className="text-sm text-muted">Menu</span>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="grid size-9 place-items-center rounded-lg hover:bg-chip"
            aria-label="Fechar menu"
          >
            <X className="size-5" />
          </button>
        </div>

        <div className="vx-scroll flex min-h-0 flex-1 flex-col overflow-y-auto px-3 pb-3 lg:pt-5">
          <nav className="space-y-1">
            {SECTIONS.map(({ slug, label, href, icon: Icon }) => {
              const active = isActive(href);
              return (
                <Link
                  key={slug}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-3.5 rounded-xl px-4 py-2.5 text-[15px] transition ${
                    active ? "vx-active text-fg" : "text-muted hover:bg-chip hover:text-fg"
                  }`}
                >
                  <Icon className={`size-5 ${active ? "text-accent" : ""}`} />
                  {label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-6 flex items-center justify-between px-2">
            <p className="text-xs font-medium uppercase tracking-wider text-subtle">Conversas</p>
            <Link
              href="/"
              className="grid size-7 place-items-center rounded-md text-muted hover:bg-chip hover:text-fg"
              aria-label="Nova conversa"
              title="Nova conversa"
            >
              <Plus className="size-4" />
            </Link>
          </div>
          <div className="mt-2 space-y-0.5">
            {conversationsLoaded && conversations.length === 0 && (
              <p className="px-3 py-2 text-sm text-subtle">Suas conversas aparecem aqui.</p>
            )}
            {conversations.map((c) => (
              <ConversationItem key={c.id} conv={c} active={c.id === activeConv} />
            ))}
          </div>
        </div>

        <div className="relative m-3 overflow-hidden rounded-2xl border border-line">
          <RioSkyline className="absolute inset-0 h-full w-full" />
          <div className="relative bg-gradient-to-b from-bg/90 via-bg/50 to-transparent p-4 pb-20">
            <p className="flex items-baseline gap-1.5">
              <span className="vx-title text-lg tracking-[0.16em]">VORTEX</span>
              <span className="text-[10px] text-muted">v0.2.1</span>
            </p>
            <p className="mt-1 text-xs text-muted">Inteligência. Liberdade. Possibilidades.</p>
            <a
              href="https://github.com/TheVortexClub/vortex"
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-line bg-panel px-3 py-1.5 text-sm hover:border-accent"
            >
              Saiba mais <ArrowRight className="size-3.5" />
            </a>
          </div>
        </div>
      </aside>
    </>
  );
}
