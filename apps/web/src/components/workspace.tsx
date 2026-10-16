"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  api,
  type Conversation,
  type ModelInfo,
  type Project,
  type Usage,
  type UserSettings,
} from "@/lib/api";

/** Data shared by the sidebar, the chat, the right panel and the pages. */
type WorkspaceValue = {
  conversations: Conversation[];
  conversationsLoaded: boolean;
  refreshConversations: () => Promise<void>;
  projects: Project[];
  projectsLoaded: boolean;
  refreshProjects: () => Promise<void>;
  models: ModelInfo[];
  /** The user's chosen default model, or the server default. */
  defaultModel: ModelInfo | undefined;
  settings: UserSettings | null;
  refreshSettings: () => Promise<void>;
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
  const [conversationsLoaded, setConversationsLoaded] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoaded, setProjectsLoaded] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const refreshConversations = useCallback(async () => {
    try {
      setConversations((await api<{ data: Conversation[] }>("/api/conversations")).data);
    } finally {
      setConversationsLoaded(true);
    }
  }, []);

  const refreshProjects = useCallback(async () => {
    try {
      setProjects((await api<{ data: Project[] }>("/api/projects")).data);
    } finally {
      setProjectsLoaded(true);
    }
  }, []);

  const refreshSettings = useCallback(async () => {
    setSettings(await api<UserSettings>("/api/settings").catch(() => null));
  }, []);

  const refreshUsage = useCallback(async () => {
    setUsage(await api<Usage>("/api/usage").catch(() => null));
  }, []);

  useEffect(() => {
    void refreshConversations().catch(() => {});
    void refreshProjects().catch(() => {});
    void refreshSettings();
    void refreshUsage();
    api<{ data: ModelInfo[] }>("/api/models")
      .then((res) => setModels(res.data.filter((m) => m.kind === "chat")))
      .catch(() => {});
  }, [refreshConversations, refreshProjects, refreshSettings, refreshUsage]);

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

  const defaultModel =
    models.find((m) => m.id === settings?.default_model) ?? models.find((m) => m.default) ?? models[0];

  const value = useMemo(
    () => ({
      conversations,
      conversationsLoaded,
      refreshConversations,
      projects,
      projectsLoaded,
      refreshProjects,
      models,
      defaultModel,
      settings,
      refreshSettings,
      usage,
      refreshUsage,
      sidebarOpen,
      setSidebarOpen,
      paletteOpen,
      setPaletteOpen,
    }),
    [
      conversations,
      conversationsLoaded,
      refreshConversations,
      projects,
      projectsLoaded,
      refreshProjects,
      models,
      defaultModel,
      settings,
      refreshSettings,
      usage,
      refreshUsage,
      sidebarOpen,
      paletteOpen,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace outside WorkspaceProvider");
  return ctx;
}
