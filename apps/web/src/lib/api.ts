// All requests go to the same origin; next.config.ts proxies /api and /v1 to the Vortex API.

export type Mode = "conversar" | "criar" | "analisar" | "programar" | "planejar" | "automatizar";

export type User = { id: string; email: string; name: string; is_admin: boolean };

export type Me = { user: User; local_mode: boolean; allow_registration: boolean };

export type Conversation = {
  id: string;
  title: string;
  model: string | null;
  mode: Mode;
  pinned: boolean;
  project_id: string | null;
  created_at: string;
  updated_at: string;
};

export type Message = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  reasoning: string | null;
  model: string | null;
  status: "ok" | "cancelled" | "error";
  feedback: number | null;
  attachments: Attachment[];
  sources: Source[];
  tool: { type: "image"; job_id: string } | null;
  created_at: string;
};

export type Attachment = { id: string; name: string; kind: FileKind; size: number };
export type FileSource = { type?: undefined; file_id: string; name: string; page: number | null };
export type WebSource = { type: "web"; n: number; title: string; url: string };
export type Source = FileSource | WebSource;

export type ModelInfo = {
  id: string;
  kind: "chat" | "embedding";
  display_name: string;
  version: string;
  badge: string | null;
  description: string;
  capabilities: string[];
  context_window: number | null;
  default: boolean;
};

export type Usage = {
  requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  avg_latency_ms: number | null;
  avg_ttft_ms: number | null;
  avg_tokens_per_sec: number | null;
  plan: { name: string; credits: string };
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
  }
}

export async function toApiError(res: Response): Promise<ApiError> {
  let message = `Erro ${res.status}`;
  let code: string | undefined;
  try {
    const body = await res.json();
    if (body?.error?.message) {
      message = body.error.message;
      code = body.error.code ?? undefined;
    } else if (typeof body?.detail === "string") {
      message = body.detail;
    } else if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      message = String(body.detail[0].msg).replace(/^Value error, /, "");
    }
  } catch {
    // non-JSON error body
  }
  if (res.status === 502 || res.status === 503) {
    message = message.startsWith("Erro") ? "O servidor do Vortex não está respondendo." : message;
  }
  return new ApiError(res.status, message, code);
}

type Options = Omit<RequestInit, "body" | "headers"> & {
  json?: unknown;
  headers?: Record<string, string>;
};

export async function api<T>(path: string, { json, headers, ...init }: Options = {}): Promise<T> {
  const res = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers: {
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : undefined,
  });
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof TypeError) return "Sem conexão com o servidor do Vortex.";
  return e instanceof Error ? e.message : String(e);
}

// ---------------------------------------------------------------- step 4

export type ProjectColor = "blue" | "violet" | "pink" | "amber" | "emerald" | "cyan";

export type Project = {
  id: string;
  name: string;
  description: string;
  instructions: string;
  color: ProjectColor;
  conversation_count: number;
  created_at: string;
  updated_at: string;
  last_activity: string;
};

export type ToolInfo = {
  id: string;
  label: string;
  description: string;
  step: number;
  available: boolean;
  enabled: boolean;
};

export type UserSettings = {
  default_model: string | null;
  temperature: number | null;
  max_tokens: number | null;
  custom_instructions: string;
  memory_enabled: boolean;
  tools: ToolInfo[];
};

export type UsageHistory = {
  days: { date: string; requests: number; tokens: number }[];
  models: {
    model: string;
    requests: number;
    tokens: number;
    avg_latency_ms: number | null;
    avg_tokens_per_sec: number | null;
  }[];
};

export type SystemStats = {
  platform: string;
  cpu: { name: string; cores: number; percent: number };
  memory: { total_gb: number; used_gb: number; percent: number };
  gpus: {
    name: string;
    memory_total_mb: number | null;
    memory_used_mb: number | null;
    utilization: number | null;
    compute: string | null;
  }[];
  loaded_models: { name: string; size_gb: number; processor: string }[] | null;
};

export type AdminUser = {
  id: string;
  email: string;
  name: string;
  is_admin: boolean;
  created_at: string;
  conversations: number;
  last_activity: string | null;
};

export type ServerInfo = {
  version: string;
  local_mode: boolean;
  allow_registration: boolean;
  users: number;
  conversations: number;
  messages: number;
};

// ---------------------------------------------------------------- step 5

export type FileKind = "pdf" | "docx" | "xlsx" | "csv" | "text" | "image";

export type FileInfo = {
  id: string;
  name: string;
  kind: FileKind;
  mime: string;
  size: number;
  status: "processing" | "ready" | "error";
  error: string | null;
  pages: number | null;
  chars: number;
  ocr: boolean;
  embedded: boolean;
  project_id: string | null;
  conversation_id: string | null;
  created_at: string;
};

export type MemoryItem = {
  id: string;
  content: string;
  source: "manual" | "chat";
  conversation_id: string | null;
  created_at: string;
  updated_at: string;
};

export const ACCEPTED_FILES =
  ".pdf,.docx,.xlsx,.csv,.tsv,.txt,.md,.json,.xml,.yaml,.yml,.log,.py,.js,.ts,.tsx,.jsx,.java,.c,.cpp,.h,.cs,.go,.rs,.php,.rb,.sql,.sh,.css,.html,.png,.jpg,.jpeg,.webp,.bmp";

/** Upload one file; resolves when the server has stored it (text extraction continues in the background). */
export async function uploadFile(
  file: File,
  target: { project_id?: string | null; conversation_id?: string | null } = {},
): Promise<FileInfo> {
  const form = new FormData();
  form.append("file", file);
  if (target.project_id) form.append("project_id", target.project_id);
  if (target.conversation_id) form.append("conversation_id", target.conversation_id);
  const res = await fetch("/api/files", { method: "POST", body: form, credentials: "same-origin" });
  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as FileInfo;
}

/** Poll until the server finished reading the file. */
export async function waitForFile(id: string, signal?: AbortSignal): Promise<FileInfo> {
  for (;;) {
    const info = await api<FileInfo>(`/api/files/${id}`);
    if (info.status !== "processing" || signal?.aborted) return info;
    await new Promise((r) => setTimeout(r, 800));
  }
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// ---------------------------------------------------------------- step 6

export type ToolStatus = ToolInfo & { reason: string };

export type Job = {
  id: string;
  kind: "image" | "video";
  prompt: string;
  params: Record<string, unknown>;
  status: "queued" | "running" | "done" | "error";
  progress: number;
  error: string | null;
  result_file_ids: string[];
  files: FileInfo[];
  conversation_id: string | null;
  created_at: string;
  finished_at: string | null;
};

export type CodeResult = {
  exit_code: number;
  stdout: string;
  stderr: string;
  duration: number;
  timed_out: boolean;
  images: FileInfo[];
};
