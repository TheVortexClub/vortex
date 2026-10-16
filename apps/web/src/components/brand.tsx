import { useId } from "react";

/** The Vortex swirl mark. */
export function VortexMark({ className = "size-9" }: { className?: string }) {
  const id = useId();
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs>
        <linearGradient id={`${id}-g`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#7dd3fc" />
          <stop offset="0.5" stopColor="#3b82f6" />
          <stop offset="1" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
      <g fill="none" stroke={`url(#${id}-g)`} strokeLinecap="round">
        <path d="M32 6a26 26 0 1 1-24.7 18" strokeWidth="4.5" />
        <path d="M32 15a17 17 0 1 1-16.2 11.8" strokeWidth="4" opacity="0.85" />
        <path d="M32 24a8 8 0 1 1-7.6 5.5" strokeWidth="3.5" opacity="0.7" />
      </g>
    </svg>
  );
}

export function VortexWordmark({ version = true }: { version?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <VortexMark />
      <span className="vx-title text-xl font-light tracking-[0.18em] sm:text-2xl">VORTEX</span>
      {version && <span className="mt-1.5 hidden text-xs text-subtle sm:inline">v0.2.1</span>}
    </span>
  );
}
