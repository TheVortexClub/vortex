// All requests go to the same origin; next.config.ts proxies /api and /v1 to the Vortex API.

export type Mode = "conversar" | "criar" | "analisar" | "programar" | "planejar" | "automatizar";

export type User = { id: string; email: string; name: string };

export type Me = { user: User; local_mode: boolean; allow_registration: boolean };

export type Conversation = {
  id: string;
  title: string;
  model: string | null;
  mode: Mode;
  pinned: boolean;
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
  created_at: string;
};

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
