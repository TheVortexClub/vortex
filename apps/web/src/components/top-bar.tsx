"use client";

import { Bell, ChevronDown, LogOut, Menu, Search, Settings } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { VortexWordmark } from "./brand";
import { useSession } from "./session";
import { ThemeToggle } from "./theme";
import { useWorkspace } from "./workspace";

function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close]);
  return ref;
}

export function TopBar() {
  const { setSidebarOpen, setPaletteOpen } = useWorkspace();
  const { state, logout } = useSession();
  const [menu, setMenu] = useState<"bell" | "user" | null>(null);
  const close = () => setMenu(null);
  const bellRef = useDismiss(menu === "bell", close);
  const userRef = useDismiss(menu === "user", close);
  const me = state.status === "ready" ? state.me : null;
  const name = me?.user.name ?? "Vortex";

  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b border-line px-3 sm:px-5">
      <button
        type="button"
        className="grid size-10 place-items-center rounded-xl text-muted hover:bg-chip hover:text-fg lg:hidden"
        aria-label="Abrir menu"
        onClick={() => setSidebarOpen(true)}
      >
        <Menu className="size-5" />
      </button>
      <Link href="/" aria-label="Vortex — início" className="shrink-0">
        <VortexWordmark />
      </Link>

      <div className="flex flex-1 justify-center px-2">
        <button
          type="button"
          onClick={() => setPaletteOpen(true)}
          className="hidden h-11 w-full max-w-xl items-center gap-3 rounded-xl border border-line bg-panel px-4 text-left text-sm text-subtle transition hover:border-line-strong md:flex"
        >
          <Search className="size-4" />
          <span className="flex-1 truncate">Pesquise conversas, arquivos, ferramentas...</span>
          <kbd className="rounded-md border border-line px-1.5 py-0.5 text-xs text-muted">Ctrl K</kbd>
        </button>
      </div>

      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => setPaletteOpen(true)}
          className="grid size-10 place-items-center rounded-xl text-muted hover:bg-chip hover:text-fg md:hidden"
          aria-label="Pesquisar"
        >
          <Search className="size-5" />
        </button>
        <ThemeToggle />
        <div className="relative hidden sm:block" ref={bellRef}>
          <button
            type="button"
            onClick={() => setMenu(menu === "bell" ? null : "bell")}
            className="grid size-10 place-items-center rounded-xl text-muted hover:bg-chip hover:text-fg"
            aria-label="Notificações"
            aria-expanded={menu === "bell"}
          >
            <Bell className="size-5" />
          </button>
          {menu === "bell" && (
            <div className="vx-panel absolute right-0 top-12 z-40 w-72 p-4 text-sm shadow-2xl" role="dialog">
              <p className="font-medium">Notificações</p>
              <p className="mt-2 text-muted">Nenhuma notificação por enquanto.</p>
            </div>
          )}
        </div>

        <div className="relative ml-1" ref={userRef}>
          <button
            type="button"
            onClick={() => setMenu(menu === "user" ? null : "user")}
            className="flex items-center gap-2.5 rounded-xl py-1 pl-1 pr-2 hover:bg-chip"
            aria-label="Menu do usuário"
            aria-expanded={menu === "user"}
          >
            <span className="grid size-10 place-items-center rounded-full border border-line-strong text-lg font-medium">
              {name.slice(0, 1).toUpperCase()}
            </span>
            <span className="hidden text-left leading-tight sm:block">
              <span className="block text-sm font-medium">{name}</span>
              <span className="block text-xs text-subtle">v0.2.1</span>
            </span>
            <ChevronDown className="hidden size-4 text-subtle sm:block" />
          </button>
          {menu === "user" && (
            <div className="vx-panel absolute right-0 top-14 z-40 w-64 p-2 text-sm shadow-2xl" role="menu">
              <div className="px-3 py-2">
                <p className="font-medium">{name}</p>
                <p className="truncate text-xs text-muted">
                  {me?.local_mode ? "Modo local (sem login)" : me?.user.email}
                </p>
              </div>
              <Link
                href="/configuracoes"
                onClick={close}
                className="flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-chip"
                role="menuitem"
              >
                <Settings className="size-4" /> Configurações
              </Link>
              {me && !me.local_mode && (
                <button
                  type="button"
                  onClick={() => void logout()}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left hover:bg-chip"
                  role="menuitem"
                >
                  <LogOut className="size-4" /> Sair
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
