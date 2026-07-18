"use client";

import { useEffect, useRef } from "react";

/**
 * Ambient AI background — replaces the old green "laser scan" line.
 *
 * A very low-opacity field of drifting nodes with connecting lines, plus the
 * occasional brighter blue/purple dot. Canvas (not DOM/Framer) because dozens of
 * continuously moving points would thrash React; one rAF loop on a fixed,
 * pointer-events-none layer costs far less.
 *
 * Deliberately barely perceptible: movement is ~4px/second and peak alpha is
 * 0.10, so it reads as texture rather than animation. Fully disabled under
 * prefers-reduced-motion, and paused when the tab is hidden.
 */
export default function BackgroundField() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const BLUE = "91, 94, 247";   // --color-brand
    const PURPLE = "139, 92, 246"; // --color-ai-solid
    const COUNT = 34;
    const LINK_DIST = 170;

    let raf = 0;
    let w = 0;
    let h = 0;
    let dpr = 1;

    type P = { x: number; y: number; vx: number; vy: number; r: number; glow: boolean };
    let pts: P[] = [];

    const seed = (): P => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.09, // ≈4px/s drift
      vy: (Math.random() - 0.5) * 0.09,
      r: Math.random() * 1.4 + 0.8,
      glow: Math.random() < 0.22,
    });

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      pts = Array.from({ length: COUNT }, seed);
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);

      // Connecting lines — fade with distance so the mesh stays whisper-quiet.
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const dx = pts[i].x - pts[j].x;
          const dy = pts[i].y - pts[j].y;
          const d = Math.hypot(dx, dy);
          if (d < LINK_DIST) {
            ctx.strokeStyle = `rgba(${BLUE}, ${0.05 * (1 - d / LINK_DIST)})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(pts[i].x, pts[i].y);
            ctx.lineTo(pts[j].x, pts[j].y);
            ctx.stroke();
          }
        }
      }

      for (const p of pts) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < -20) p.x = w + 20;
        if (p.x > w + 20) p.x = -20;
        if (p.y < -20) p.y = h + 20;
        if (p.y > h + 20) p.y = -20;

        const tone = p.glow ? PURPLE : BLUE;
        if (p.glow) {
          const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 7);
          g.addColorStop(0, `rgba(${tone}, 0.10)`);
          g.addColorStop(1, `rgba(${tone}, 0)`);
          ctx.fillStyle = g;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r * 7, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = `rgba(${tone}, ${p.glow ? 0.16 : 0.10})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }

      raf = requestAnimationFrame(draw);
    };

    const start = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); };
    const stop = () => cancelAnimationFrame(raf);
    const onVisibility = () => (document.hidden ? stop() : start());

    resize();
    start();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0 select-none"
    />
  );
}
