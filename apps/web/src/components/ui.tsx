"use client";

import { X } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import type { ProjectColor } from "@/lib/api";

/** Small shared building blocks for the pages (kept minimal on purpose). */

export const inputClass =
  "w-full rounded-xl border border-line bg-elev/70 px-3.5 py-2.5 text-[15px] outline-none focus:border-accent";

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-subtle">{hint}</span>}
    </label>
  );
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-accent text-white shadow-[0_0_18px_var(--accent-glow)] hover:brightness-110",
    ghost: "border border-line hover:border-line-strong hover:bg-chip",
    danger: "border border-bad/50 text-bad hover:bg-bad/10",
  }[variant];
  return (
    <button
      type="button"
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${styles} ${className}`}
    />
  );
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold">{title}</h1>
        {description && <p className="mt-1 text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    ref.current?.querySelector<HTMLElement>("input, textarea, select, button")?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 backdrop-blur-sm" onMouseDown={onClose}>
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={id}
        onMouseDown={(e) => e.stopPropagation()}
        className="vx-panel w-full max-w-lg p-6 shadow-2xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 id={id} className="text-lg font-semibold">
            {title}
          </h2>
          <button type="button" onClick={onClose} aria-label="Fechar" className="rounded-lg p-1 hover:bg-chip">
            <X className="size-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export const PROJECT_COLORS: Record<ProjectColor, { bg: string; fg: string; label: string }> = {
  blue: { bg: "bg-blue-500/20", fg: "text-blue-400", label: "Azul" },
  violet: { bg: "bg-violet-500/20", fg: "text-violet-400", label: "Violeta" },
  pink: { bg: "bg-pink-500/20", fg: "text-pink-400", label: "Rosa" },
  amber: { bg: "bg-amber-500/20", fg: "text-amber-400", label: "Âmbar" },
  emerald: { bg: "bg-emerald-500/20", fg: "text-emerald-400", label: "Verde" },
  cyan: { bg: "bg-cyan-500/20", fg: "text-cyan-400", label: "Ciano" },
};

export function Toggle({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition disabled:opacity-40 ${
        checked ? "bg-accent" : "bg-line-strong"
      }`}
    >
      <span
        className={`absolute top-0.5 size-5 rounded-full bg-white shadow transition-all ${
          checked ? "left-[22px]" : "left-0.5"
        }`}
      />
    </button>
  );
}
