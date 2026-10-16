"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { VortexMark } from "./brand";
import { CommandPalette } from "./command-palette";
import { useSession } from "./session";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";
import { WorkspaceProvider } from "./workspace";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { state, reload } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (state.status === "anonymous") router.replace("/login");
  }, [state.status, router]);

  if (state.status === "offline") {
    return (
      <div className="grid min-h-screen place-items-center p-6 text-center">
        <div className="vx-panel max-w-md p-8">
          <VortexMark className="mx-auto size-12" />
          <p className="mt-4 font-medium">{state.error}</p>
          <p className="mt-2 text-sm text-muted">Verifique se a API do Vortex está rodando no servidor.</p>
          <button
            type="button"
            onClick={() => void reload()}
            className="mt-5 rounded-xl bg-accent px-4 py-2 text-sm text-white"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  if (state.status !== "ready") {
    return (
      <div className="grid min-h-screen place-items-center" role="status" aria-label="Carregando">
        <VortexMark className="size-12 animate-spin [animation-duration:3s]" />
      </div>
    );
  }

  return (
    <WorkspaceProvider>
      <div className="flex h-dvh flex-col">
        <TopBar />
        <div className="flex min-h-0 flex-1">
          <Sidebar />
          <main className="min-w-0 flex-1">{children}</main>
        </div>
      </div>
      <CommandPalette />
    </WorkspaceProvider>
  );
}
