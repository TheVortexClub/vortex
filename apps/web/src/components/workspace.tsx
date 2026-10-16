"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, type Conversation, type ModelInfo, type Usage } from "@/lib/api";

/** Data shared by the sidebar, the chat and the right panel. */
type WorkspaceValue = {
  conversations: Conversation[];
  conversationsLoaded: boolean;
  refreshConversations: () => Promise<void>;
  models: ModelInfo[];
  defaultModel: ModelInfo | undefined;
  usage: Usage | null;
  refreshUsage: () => Promise<void>;
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  paletteOpen: boolean;
  setPaletteOpen: (open: boolean) => void;
};

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationsLoaded, setLoaded] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const refreshConversations = useCallback(async () => {
    try {
      const res = await api<{ data: Conversation[] }>("/api/conversations");
      setConversations(res.data);
    } finally {
      setLoaded(true);
    }
  }, []);

  const refreshUsage = useCallback(async () => {
    setUsage(await api<Usage>("/api/usage").catch(() => null));
  }, []);

  useEffect(() => {
    void refreshConversations().catch(() => {});
    void refreshUsage();
    api<{ data: ModelInfo[] }>("/api/models")
      .then((res) => setModels(res.data.filter((m) => m.kind === "chat")))
      .catch(() => {});
  }, [refreshConversations, refreshUsage]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const value = useMemo(
    () => ({
      conversations,
      conversationsLoaded,
      refreshConversations,
      models,
      defaultModel: models.find((m) => m.default) ?? models[0],
      usage,
      refreshUsage,
      sidebarOpen,
      setSidebarOpen,
      paletteOpen,
      setPaletteOpen,
    }),
    [conversations, conversationsLoaded, refreshConversations, models, usage, refreshUsage, sidebarOpen, paletteOpen],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace outside WorkspaceProvider");
  return ctx;
}
