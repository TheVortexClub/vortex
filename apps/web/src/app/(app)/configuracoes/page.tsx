"use client";

import { Check, Copy, Download, Shield, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useSession } from "@/components/session";
import { useTheme } from "@/components/theme";
import { Button, Field, inputClass, PageHeader, Toggle } from "@/components/ui";
import { useWorkspace } from "@/components/workspace";
import { api, type AdminUser, errorMessage, type ServerInfo, type UserSettings } from "@/lib/api";
import { copyText, timeAgo } from "@/lib/text";

type Tab = "perfil" | "modelo" | "ferramentas" | "dados" | "api" | "servidor";

export default function SettingsPage() {
  const { state } = useSession();
  const me = state.status === "ready" ? state.me : null;
  const [tab, setTab] = useState<Tab>("perfil");
  const tabs: [Tab, string][] = [
    ["perfil", "Perfil"],
    ["modelo", "Modelo"],
    ["ferramentas", "Ferramentas"],
    ["dados", "Dados"],
    ["api", "Acesso à API"],
    ...(me?.user.is_admin ? ([["servidor", "Servidor"]] as [Tab, string][]) : []),
  ];

  return (
    <div className="vx-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <PageHeader title="Configurações" />
        <div role="tablist" aria-label="Seções" className="mb-6 flex gap-1 overflow-x-auto border-b border-line">
          {tabs.map(([id, label]) => (
            <button
              key={id}
              role="tab"
              type="button"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm transition ${
                tab === id ? "border-accent text-fg" : "border-transparent text-muted hover:text-fg"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div role="tabpanel">
          {tab === "perfil" && <ProfileTab />}
          {tab === "modelo" && <ModelTab />}
          {tab === "ferramentas" && <ToolsTab />}
          {tab === "dados" && <DataTab />}
          {tab === "api" && <ApiTab />}
          {tab === "servidor" && <ServerTab />}
        </div>
      </div>
    </div>
  );
}

function Saved({ show }: { show: boolean }) {
  return show ? (
    <span className="inline-flex items-center gap-1 text-sm text-ok" role="status">
      <Check className="size-4" /> Salvo
    </span>
  ) : null;
}

function ErrorLine({ text }: { text: string | null }) {
  return text ? (
    <p role="alert" className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm">
      {text}
    </p>
  ) : null;
}

function useFlash() {
  const [on, setOn] = useState(false);
  return [on, () => { setOn(true); setTimeout(() => setOn(false), 1800); }] as const;
}

// ---------------------------------------------------------------- Perfil

function ProfileTab() {
  const { state, reload } = useSession();
  const { theme, toggle } = useTheme();
  const me = state.status === "ready" ? state.me : null;
  const [name, setName] = useState(me?.user.name ?? "");
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [error, setError] = useState<string | null>(null);
  const [saved, flash] = useFlash();
  const [pwSaved, flashPw] = useFlash();

  return (
    <div className="space-y-8">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          try {
            await api("/api/auth/me", { method: "PATCH", json: { name } });
            await reload();
            flash();
          } catch (err) {
            setError(errorMessage(err));
          }
        }}
      >
        <Field label="Nome">
          <input className={inputClass} value={name} maxLength={100} required onChange={(e) => setName(e.target.value)} />
        </Field>
        {me && !me.local_mode && <p className="text-sm text-muted">E-mail: {me.user.email}</p>}
        <div className="flex items-center gap-3">
          <Button type="submit">Salvar</Button>
          <Saved show={saved} />
        </div>
      </form>

      <div className="flex items-center justify-between rounded-xl border border-line p-4">
        <div>
          <p className="font-medium">Tema escuro</p>
          <p className="text-sm text-muted">Também dá para trocar pelo ícone no topo.</p>
        </div>
        <Toggle label="Tema escuro" checked={theme === "dark"} onChange={toggle} />
      </div>

      {me && !me.local_mode && (
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            try {
              await api("/api/auth/password", { method: "POST", json: pw });
              setPw({ current_password: "", new_password: "" });
              flashPw();
            } catch (err) {
              setError(errorMessage(err));
            }
          }}
        >
          <h2 className="font-medium">Trocar senha</h2>
          <Field label="Senha atual">
            <input
              type="password"
              autoComplete="current-password"
              className={inputClass}
              required
              value={pw.current_password}
              onChange={(e) => setPw({ ...pw, current_password: e.target.value })}
            />
          </Field>
          <Field label="Nova senha" hint="Mínimo de 8 caracteres.">
            <input
              type="password"
              autoComplete="new-password"
              minLength={8}
              className={inputClass}
              required
              value={pw.new_password}
              onChange={(e) => setPw({ ...pw, new_password: e.target.value })}
            />
          </Field>
          <div className="flex items-center gap-3">
            <Button type="submit">Trocar senha</Button>
            <Saved show={pwSaved} />
          </div>
        </form>
      )}
      <ErrorLine text={error} />
    </div>
  );
}

// ---------------------------------------------------------------- Modelo

function ModelTab() {
  const { models, settings, refreshSettings } = useWorkspace();
  const [draft, setDraft] = useState<Partial<UserSettings>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, flash] = useFlash();

  useEffect(() => {
    if (settings) setDraft(settings);
  }, [settings]);

  if (!settings) return <p className="text-subtle">Carregando…</p>;

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api("/api/settings", {
        method: "PATCH",
        json: {
          default_model: draft.default_model || null,
          temperature: draft.temperature ?? null,
          max_tokens: draft.max_tokens ?? null,
          custom_instructions: draft.custom_instructions ?? "",
        },
      });
      await refreshSettings();
      flash();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <form onSubmit={save} className="space-y-5">
      <Field label="Modelo padrão" hint="Usado nas conversas novas. Dá para trocar em cada conversa pelo seletor.">
        <select
          className={inputClass}
          value={draft.default_model ?? ""}
          onChange={(e) => setDraft({ ...draft, default_model: e.target.value || null })}
        >
          <option value="">Padrão do servidor</option>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.display_name}
              {m.badge ? ` (${m.badge})` : ""}
            </option>
          ))}
        </select>
      </Field>

      <Field
        label={`Temperatura: ${draft.temperature ?? "padrão (0,7)"}`}
        hint="Mais baixa = respostas mais previsíveis. Mais alta = mais criativas."
      >
        <div className="flex items-center gap-3">
          <input
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={draft.temperature ?? 0.7}
            onChange={(e) => setDraft({ ...draft, temperature: Number(e.target.value) })}
            className="flex-1 accent-[var(--accent)]"
            aria-label="Temperatura"
          />
          <button type="button" className="text-sm text-accent" onClick={() => setDraft({ ...draft, temperature: null })}>
            Padrão
          </button>
        </div>
      </Field>

      <Field label="Tamanho máximo da resposta (tokens)" hint="Vazio = padrão do modelo (2048).">
        <input
          type="number"
          min={16}
          max={32768}
          className={inputClass}
          value={draft.max_tokens ?? ""}
          onChange={(e) => setDraft({ ...draft, max_tokens: e.target.value ? Number(e.target.value) : null })}
        />
      </Field>

      <Field
        label="Instruções personalizadas"
        hint="O Vortex considera em todas as suas conversas. Ex.: quem você é, como prefere as respostas."
      >
        <textarea
          className={`${inputClass} min-h-28`}
          maxLength={4000}
          value={draft.custom_instructions ?? ""}
          onChange={(e) => setDraft({ ...draft, custom_instructions: e.target.value })}
          placeholder="Ex.: Sou desenvolvedor de jogos. Prefiro respostas curtas com exemplos de código."
        />
      </Field>
      <ErrorLine text={error} />
      <div className="flex items-center gap-3">
        <Button type="submit">Salvar</Button>
        <Saved show={saved} />
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- Ferramentas

function ToolsTab() {
  const { tools, refreshSettings, refreshTools } = useWorkspace();
  if (tools.length === 0) return <p className="text-subtle">Carregando…</p>;
  const set = async (id: string, on: boolean) => {
    await api("/api/settings", { method: "PATCH", json: { tools: { [id]: on } } });
    await Promise.all([refreshSettings(), refreshTools()]);
  };
  return (
    <div className="space-y-2">
      <p className="mb-4 text-sm text-muted">
        Escolha o que o Vortex pode usar nas suas conversas. Tudo roda no servidor; nada é enviado para fora, exceto a
        pesquisa na web quando ligada.
      </p>
      {tools.map((t) => (
        <div key={t.id} className="flex items-center gap-4 rounded-xl border border-line p-4">
          <div className="min-w-0 flex-1">
            <p className="font-medium">
              {t.label}
              {!t.available && (
                <span className="ml-2 rounded-md bg-chip px-2 py-0.5 text-[11px] text-subtle">indisponível</span>
              )}
            </p>
            <p className="text-sm text-muted">{t.description}</p>
            {!t.available && <p className="mt-1 text-xs text-warn">{t.reason}</p>}
          </div>
          <Toggle label={t.label} checked={t.enabled} disabled={t.step > 6} onChange={(v) => void set(t.id, v)} />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------- Dados

function DataTab() {
  const { state, logout } = useSession();
  const { refreshConversations, refreshProjects } = useWorkspace();
  const me = state.status === "ready" ? state.me : null;
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-line p-4">
        <h2 className="font-medium">Exportar meus dados</h2>
        <p className="mt-1 text-sm text-muted">Baixa um arquivo JSON com suas conversas, projetos e configurações.</p>
        <a
          href="/api/settings/export"
          className="mt-3 inline-flex items-center gap-2 rounded-xl border border-line px-4 py-2 text-sm hover:border-accent"
        >
          <Download className="size-4" /> Baixar (.json)
        </a>
      </section>

      <section className="rounded-xl border border-line p-4">
        <h2 className="font-medium">Apagar todas as conversas</h2>
        <p className="mt-1 text-sm text-muted">Não dá para desfazer. Seus projetos continuam.</p>
        <Button
          variant="danger"
          className="mt-3"
          onClick={async () => {
            if (!window.confirm("Apagar TODAS as suas conversas? Não dá para desfazer.")) return;
            const res = await api<{ deleted: number }>("/api/conversations", { method: "DELETE" });
            await Promise.all([refreshConversations(), refreshProjects()]);
            setMsg(`${res.deleted} conversas apagadas.`);
          }}
        >
          <Trash2 className="size-4" /> Apagar conversas
        </Button>
        {msg && <p className="mt-2 text-sm text-ok" role="status">{msg}</p>}
      </section>

      {me && !me.local_mode && (
        <section className="rounded-xl border border-bad/40 p-4">
          <h2 className="font-medium text-bad">Excluir minha conta</h2>
          <p className="mt-1 text-sm text-muted">Apaga a conta e todos os seus dados deste servidor.</p>
          <form
            className="mt-3 flex flex-wrap gap-2"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              if (!window.confirm("Excluir sua conta e todos os seus dados?")) return;
              try {
                await api("/api/auth/me", { method: "DELETE", json: { password } });
                await logout();
              } catch (err) {
                setError(errorMessage(err));
              }
            }}
          >
            <input
              type="password"
              required
              placeholder="Sua senha"
              autoComplete="current-password"
              aria-label="Senha para confirmar"
              className={`${inputClass} max-w-xs`}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button type="submit" variant="danger">
              Excluir conta
            </Button>
          </form>
          <div className="mt-2">
            <ErrorLine text={error} />
          </div>
        </section>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- API

function ApiTab() {
  const { state } = useSession();
  const localMode = state.status === "ready" && state.me.local_mode;
  const [base, setBase] = useState("");
  const [lang, setLang] = useState<"curl" | "python" | "js">("curl");
  useEffect(() => setBase(window.location.origin), []);

  const auth = localMode ? "" : ' \\\n  -H "Authorization: Bearer $VORTEX_TOKEN"';
  const examples = {
    curl: `${localMode ? "" : `# 1. Faça login e copie o access_token
curl -X POST ${base}/api/auth/login -H "Content-Type: application/json" \\
  -d '{"email": "voce@exemplo.com", "password": "sua-senha"}'

# 2. Converse com o Vortex
`}curl ${base}/v1/chat/completions${auth} \\
  -H "Content-Type: application/json" \\
  -d '{"model": "vortex-v0.2.1", "messages": [{"role": "user", "content": "Olá!"}]}'`,
    python: `from openai import OpenAI  # qualquer cliente no formato OpenAI funciona

client = OpenAI(base_url="${base}/v1", api_key=${localMode ? '"nao-precisa"' : '"<seu access_token>"'})
resposta = client.chat.completions.create(
    model="vortex-v0.2.1",
    messages=[{"role": "user", "content": "Olá!"}],
)
print(resposta.choices[0].message.content)`,
    js: `const res = await fetch("${base}/v1/chat/completions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",${localMode ? "" : '\n    Authorization: "Bearer <seu access_token>",'}
  },
  body: JSON.stringify({
    model: "vortex-v0.2.1",
    messages: [{ role: "user", content: "Olá!" }],
  }),
});
console.log((await res.json()).choices[0].message.content);`,
  }[lang];

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        A API do Vortex usa o mesmo formato da API da OpenAI, então apps e bibliotecas existentes funcionam apontando
        para o <strong>seu</strong> servidor. Nada é enviado para a OpenAI.{" "}
        {localMode ? "No modo local não precisa de chave." : "Use o token que o login devolve (vale por algumas horas)."}
      </p>
      <div className="rounded-xl border border-line p-4 text-sm">
        <p className="text-muted">URL base</p>
        <code className="mt-1 block text-accent">{base}/v1</code>
        <p className="mt-3 text-muted">Documentação interativa</p>
        <a href="/docs" target="_blank" className="mt-1 block text-accent underline">
          {base}/docs
        </a>
      </div>
      <div className="flex gap-1" role="tablist" aria-label="Linguagem">
        {(["curl", "python", "js"] as const).map((l) => (
          <button
            key={l}
            type="button"
            role="tab"
            aria-selected={lang === l}
            onClick={() => setLang(l)}
            className={`rounded-lg px-3 py-1.5 text-sm ${lang === l ? "bg-chip text-fg" : "text-muted hover:text-fg"}`}
          >
            {{ curl: "curl", python: "Python", js: "JavaScript" }[l]}
          </button>
        ))}
      </div>
      <CodeBox code={examples} />
    </div>
  );
}

function CodeBox({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative overflow-hidden rounded-xl border border-line bg-[var(--code-bg)] text-slate-100">
      <button
        type="button"
        onClick={() => void copyText(code).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); })}
        className="absolute right-2 top-2 flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-400 hover:bg-white/10"
        aria-label="Copiar exemplo"
      >
        {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />} {copied ? "Copiado" : "Copiar"}
      </button>
      <pre className="vx-scroll overflow-x-auto p-4 text-[13px] leading-relaxed">{code}</pre>
    </div>
  );
}

// ---------------------------------------------------------------- Servidor (admin)

function ServerTab() {
  const { state } = useSession();
  const myId = state.status === "ready" ? state.me.user.id : "";
  const [info, setInfo] = useState<ServerInfo | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [i, u] = await Promise.all([
        api<ServerInfo>("/api/admin/server"),
        api<{ data: AdminUser[] }>("/api/admin/users"),
      ]);
      setInfo(i);
      setUsers(u.data);
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  useEffect(() => {
    void load();
  }, []);

  const act = async (fn: () => Promise<unknown>) => {
    setError(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  if (!info) return <ErrorLine text={error} />;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-3 text-center">
        {[
          ["Contas", info.users],
          ["Conversas", info.conversations],
          ["Mensagens", info.messages],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-line p-3">
            <p className="text-xl font-semibold tabular-nums">{Number(value).toLocaleString("pt-BR")}</p>
            <p className="text-xs text-subtle">{label}</p>
          </div>
        ))}
      </div>

      {!info.local_mode && (
        <div className="flex items-center justify-between rounded-xl border border-line p-4">
          <div>
            <p className="font-medium">Permitir novos cadastros</p>
            <p className="text-sm text-muted">Desligue quando todo mundo que deve usar já tiver conta.</p>
          </div>
          <Toggle
            label="Permitir novos cadastros"
            checked={info.allow_registration}
            onChange={(v) => void act(() => api("/api/admin/server", { method: "PATCH", json: { allow_registration: v } }))}
          />
        </div>
      )}

      <ErrorLine text={error} />

      {!info.local_mode && (
        <section>
          <h2 className="mb-2 font-medium">Contas neste servidor</h2>
          <div className="space-y-2">
            {users.map((u) => (
              <div key={u.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-line p-3 text-sm">
                <span className="grid size-9 place-items-center rounded-full border border-line-strong">
                  {u.name.slice(0, 1).toUpperCase()}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    {u.name} {u.id === myId && <span className="text-subtle">(você)</span>}
                    {u.is_admin && (
                      <span className="ml-2 inline-flex items-center gap-1 rounded-md bg-accent/15 px-1.5 py-0.5 text-[11px] text-accent">
                        <Shield className="size-3" /> admin
                      </span>
                    )}
                  </p>
                  <p className="truncate text-xs text-subtle">
                    {u.email} • {u.conversations} conversas • entrou {timeAgo(u.created_at)}
                    {u.last_activity ? ` • ativo ${timeAgo(u.last_activity)}` : ""}
                  </p>
                </div>
                {u.id !== myId && (
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      onClick={() =>
                        void act(() => api(`/api/admin/users/${u.id}`, { method: "PATCH", json: { is_admin: !u.is_admin } }))
                      }
                    >
                      {u.is_admin ? "Remover admin" : "Tornar admin"}
                    </Button>
                    <Button
                      variant="danger"
                      aria-label={`Excluir ${u.name}`}
                      onClick={() => {
                        if (window.confirm(`Excluir a conta de ${u.name} e todos os dados dela?`))
                          void act(() => api(`/api/admin/users/${u.id}`, { method: "DELETE" }));
                      }}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
