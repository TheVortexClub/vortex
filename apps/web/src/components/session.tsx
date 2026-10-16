"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ApiError, type Me } from "@/lib/api";

type SessionState =
  | { status: "loading" }
  | { status: "anonymous" }
  | { status: "offline"; error: string }
  | { status: "ready"; me: Me };

type SessionContextValue = {
  state: SessionState;
  reload: () => Promise<void>;
  logout: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: "loading" });

  const reload = useCallback(async () => {
    try {
      setState({ status: "ready", me: await api<Me>("/api/auth/me") });
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setState({ status: "anonymous" });
      else setState({ status: "offline", error: "O servidor do Vortex não está respondendo." });
    }
  }, []);

  const logout = useCallback(async () => {
    await api("/api/auth/logout", { method: "POST" }).catch(() => {});
    setState({ status: "anonymous" });
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <SessionContext.Provider value={{ state, reload, logout }}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession outside SessionProvider");
  return ctx;
}
