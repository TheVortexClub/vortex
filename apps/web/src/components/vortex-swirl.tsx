"use client";

import { useEffect, useRef } from "react";

type Particle = { r: number; a: number; speed: number; size: number; arm: number };

/** Animated galaxy-like swirl drawn on a canvas (static frame when reduced motion is on). */
export function VortexSwirl({ className = "" }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const light = document.documentElement.dataset.theme === "light";
    const arms = 3;
    const particles: Particle[] = Array.from({ length: 1600 }, (_, i) => {
      const r = Math.pow(Math.random(), 0.75);
      return {
        r,
        a: Math.random() * Math.PI * 2,
        speed: 0.0025 + Math.random() * 0.004,
        size: 0.4 + Math.random() * 1.5 * (1 - r * 0.5),
        arm: i % arms,
      };
    });

    let width = 0;
    let height = 0;
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    let raf = 0;
    const draw = () => {
      const cx = width / 2;
      const cy = height / 2;
      const R = Math.min(width / 2, height / 1.15);

      ctx.globalCompositeOperation = "destination-out";
      ctx.fillStyle = `rgba(0,0,0,${reduced ? 1 : 0.2})`;
      ctx.fillRect(0, 0, width, height);
      ctx.globalCompositeOperation = light ? "source-over" : "lighter";

      // core glow
      const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.45);
      core.addColorStop(0, light ? "rgba(99,102,241,0.35)" : "rgba(190,210,255,0.55)");
      core.addColorStop(0.35, "rgba(59,130,246,0.18)");
      core.addColorStop(1, "rgba(59,130,246,0)");
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.ellipse(cx, cy, R * 0.5, R * 0.3, -0.25, 0, Math.PI * 2);
      ctx.fill();

      for (const p of particles) {
        if (!reduced) p.a += p.speed / (p.r + 0.18);
        const spiral = p.a + p.arm * ((Math.PI * 2) / arms) + Math.log(p.r + 0.05) * 2.4;
        const jitter = Math.sin(p.a * 3 + p.r * 10) * 0.04;
        const x = cx + Math.cos(spiral) * (p.r + jitter) * R;
        const y = cy + Math.sin(spiral) * (p.r + jitter) * R * 0.58;
        const rotX = cx + (x - cx) * Math.cos(-0.25) - (y - cy) * Math.sin(-0.25);
        const rotY = cy + (x - cx) * Math.sin(-0.25) + (y - cy) * Math.cos(-0.25);
        const hue = 205 + p.r * 70; // blue → violet outward
        const alpha = (1 - p.r) * 0.85 + 0.1;
        ctx.fillStyle = `hsla(${hue}, 95%, ${light ? 55 : 68}%, ${alpha})`;
        ctx.beginPath();
        ctx.arc(rotX, rotY, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
      if (!reduced) raf = requestAnimationFrame(draw);
    };

    const start = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(draw);
    };
    start();
    const onVisibility = () => (document.hidden ? cancelAnimationFrame(raf) : start());
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return <canvas ref={ref} className={className} aria-hidden="true" />;
}
