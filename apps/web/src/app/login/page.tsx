"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { VortexMark } from "@/components/brand";
import { useSession } from "@/components/session";
import { ThemeToggle } from "@/components/theme";
import { VortexSwirl } from "@/components/vortex-swirl";
import { api, errorMessage } from "@/lib/api";

type AuthConfig = { local_mode: boolean; allow_registration: boolean };

export default function LoginPage() {
  const router = useRouter();
  const { state, reload } = useSession();
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<AuthConfig>("/api/auth/config")
      .then(setConfig)
      .catch(() => setError("O servidor do Vortex não está respondendo."));
  }, []);

  useEffect(() => {
    if (state.status === "ready" || config?.local_mode) router.replace("/");
  }, [state.status, config, router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(`/api/auth/${mode}`, {
        method: "POST",
        json: mode === "login" ? { email: form.email, password: form.password } : form,
      });
      await reload();
      router.replace("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const field =
    "mt-1 w-full rounded-xl border border-line bg-elev/70 px-3.5 py-2.5 text-[15px] outline-none focus:border-accent";

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden p-4">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <VortexSwirl className="pointer-events-none absolute left-1/2 top-1/2 h-[520px] w-[900px] -translate-x-1/2 -translate-y-1/2 opacity-40" />
      <div className="vx-panel relative w-full max-w-sm p-7">
        <div className="text-center">
          <VortexMark className="mx-auto size-12" />
          <h1 className="vx-title mt-3 text-3xl font-light tracking-[0.25em]">VORTEX</h1>
          <p className="mt-1 text-sm text-muted">
            {mode === "login" ? "Entre na sua conta" : "Crie sua conta"}
          </p>
        </div>

        <form onSubmit={submit} className="mt-6 space-y-3">
          {mode === "register" && (
            <label className="block text-sm">
              Nome
              <input
                className={field}
                value={form.name}
                maxLength={100}
                autoComplete="name"
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
          )}
          <label className="block text-sm">
            E-mail
            <input
              className={field}
              type="email"
              required
              autoComplete="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Senha
            <input
              className={field}
              type="password"
              required
              minLength={mode === "register" ? 8 : 1}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            {mode === "register" && <span className="mt-1 block text-xs text-subtle">Mínimo de 8 caracteres.</span>}
          </label>

          {error && (
            <p role="alert" className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-accent py-2.5 font-medium text-white shadow-[0_0_24px_var(--accent-glow)] hover:brightness-110 disabled:opacity-60"
          >
            {busy && <Loader2 className="size-4 animate-spin" />}
            {mode === "login" ? "Entrar" : "Criar conta"}
          </button>
        </form>

        {config?.allow_registration && (
          <p className="mt-5 text-center text-sm text-muted">
            {mode === "login" ? "Ainda não tem conta?" : "Já tem conta?"}{" "}
            <button
              type="button"
              className="text-accent hover:underline"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
            >
              {mode === "login" ? "Cadastre-se" : "Entrar"}
            </button>
          </p>
        )}
      </div>
    </main>
  );
}
