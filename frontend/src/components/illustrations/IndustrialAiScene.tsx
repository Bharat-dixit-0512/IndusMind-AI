"use client";

import { motion } from "framer-motion";

/**
 * Isometric "industrial intelligence" scene — hand-built SVG, no stock art.
 *
 * Reads as: plant assets and documents on an isometric plane, feeding a central
 * AI core, which emits a knowledge graph plus analytics. Everything is drawn
 * from design tokens so it re-themes with the rest of the system, and all
 * motion is slow/low-contrast so it stays executive-appropriate rather than
 * decorative.
 */
export default function IndustrialAiScene({ className }: { className?: string }) {
  // Shared slow pulse for the graph links.
  const link = (delay: number) => ({
    animate: { opacity: [0.18, 0.5, 0.18] },
    transition: { duration: 5, repeat: Infinity, ease: "easeInOut" as const, delay },
  });
  const nodePulse = (delay: number) => ({
    animate: { scale: [1, 1.12, 1], opacity: [0.85, 1, 0.85] },
    transition: { duration: 4.5, repeat: Infinity, ease: "easeInOut" as const, delay },
  });

  return (
    <svg
      viewBox="0 0 560 400"
      className={className}
      role="img"
      aria-label="Isometric illustration: factory assets and documents feeding an AI core that produces a knowledge graph and analytics"
    >
      <defs>
        <linearGradient id="ias-core" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--color-brand)" />
          <stop offset="100%" stopColor="var(--color-ai-solid)" />
        </linearGradient>
        <linearGradient id="ias-plate" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-brand)" stopOpacity="0.10" />
          <stop offset="100%" stopColor="var(--color-brand)" stopOpacity="0.02" />
        </linearGradient>
        <radialGradient id="ias-glow">
          <stop offset="0%" stopColor="var(--color-brand)" stopOpacity="0.28" />
          <stop offset="100%" stopColor="var(--color-brand)" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="ias-panel" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="100%" stopColor="#F4F7FC" />
        </linearGradient>
      </defs>

      {/* Ambient glow behind the core */}
      <circle cx="280" cy="180" r="140" fill="url(#ias-glow)" />

      {/* Isometric ground plate + grid */}
      <g opacity="0.9">
        <path d="M280 262 L512 324 L280 386 L48 324 Z" fill="url(#ias-plate)" />
        <path
          d="M280 262 L512 324 L280 386 L48 324 Z"
          fill="none"
          stroke="var(--color-brand)"
          strokeOpacity="0.18"
        />
        {[0.25, 0.5, 0.75].map((t) => (
          <g key={t} stroke="var(--color-brand)" strokeOpacity="0.09">
            <line x1={48 + 232 * t} y1={324 - 62 * t} x2={280 + 232 * t} y2={386 - 62 * t} />
            <line x1={280 - 232 * t} y1={386 - 62 * t} x2={512 - 232 * t} y2={324 - 62 * t} />
          </g>
        ))}
      </g>

      {/* ── Factory (left) ── */}
      <g transform="translate(86 214)">
        <path d="M0 40 L46 18 L92 40 L46 62 Z" fill="var(--color-brand)" fillOpacity="0.14" />
        <path d="M0 40 L0 16 L46 -6 L46 18 Z" fill="var(--color-surface)" stroke="var(--color-line)" />
        <path d="M46 18 L92 -6 L92 18 L46 40 Z" fill="#EEF3FB" stroke="var(--color-line)" />
        <path d="M0 16 L46 -6 L92 16 L46 38 Z" fill="var(--color-surface)" stroke="var(--color-line)" />
        {/* chimneys */}
        <rect x="18" y="-26" width="9" height="18" fill="var(--color-surface)" stroke="var(--color-line)" />
        <rect x="34" y="-34" width="9" height="26" fill="var(--color-surface)" stroke="var(--color-line)" />
        <text x="46" y="80" textAnchor="middle" className="fill-[var(--color-ink-tertiary)]" style={{ fontSize: 11, fontWeight: 700 }}>
          Assets
        </text>
      </g>

      {/* ── Documents (right) ── */}
      <g transform="translate(388 218)">
        {[0, 1, 2].map((i) => (
          <motion.g
            key={i}
            animate={{ y: [0, -3, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: i * 0.5 }}
          >
            <path
              d={`M0 ${34 - i * 11} L40 ${12 - i * 11} L80 ${34 - i * 11} L40 ${56 - i * 11} Z`}
              fill="url(#ias-panel)"
              stroke="var(--color-line)"
            />
            <line
              x1="22" y1={`${32 - i * 11}`} x2="52" y2={`${18 - i * 11}`}
              stroke="var(--color-brand)" strokeOpacity="0.35"
            />
          </motion.g>
        ))}
        <text x="40" y="86" textAnchor="middle" className="fill-[var(--color-ink-tertiary)]" style={{ fontSize: 11, fontWeight: 700 }}>
          Documents
        </text>
      </g>

      {/* ── Knowledge-graph links into the core ── */}
      <g stroke="var(--color-brand)" strokeWidth="1.5" fill="none">
        <motion.path d="M132 218 C 176 194, 220 190, 262 184" {...link(0)} />
        <motion.path d="M428 222 C 384 196, 336 190, 298 184" {...link(0.8)} />
        <motion.path d="M280 150 L200 96" {...link(1.6)} />
        <motion.path d="M280 150 L360 96" {...link(2.2)} />
        <motion.path d="M200 96 L360 96" {...link(2.8)} stroke="var(--color-ai-solid)" />
      </g>

      {/* Graph satellite nodes */}
      <motion.circle cx="200" cy="96" r="7" fill="var(--color-ai-solid)" {...nodePulse(0.3)} />
      <motion.circle cx="360" cy="96" r="7" fill="var(--color-info-solid)" {...nodePulse(1.1)} />
      <motion.circle cx="280" cy="64" r="5" fill="var(--color-brand)" {...nodePulse(1.9)} />
      <line x1="200" y1="96" x2="280" y2="64" stroke="var(--color-brand)" strokeOpacity="0.25" />
      <line x1="360" y1="96" x2="280" y2="64" stroke="var(--color-brand)" strokeOpacity="0.25" />

      {/* ── Central AI core ── */}
      <motion.g
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
      >
        <path d="M280 128 L326 156 L280 184 L234 156 Z" fill="url(#ias-core)" />
        <path d="M234 156 L234 178 L280 206 L280 184 Z" fill="var(--color-brand)" fillOpacity="0.75" />
        <path d="M326 156 L326 178 L280 206 L280 184 Z" fill="var(--color-ai-solid)" fillOpacity="0.6" />
        {/* core "circuit" marks */}
        <g stroke="#FFFFFF" strokeOpacity="0.65" strokeWidth="1.5" fill="none">
          <path d="M264 156 L274 150 L286 162 L296 156" />
          <circle cx="280" cy="156" r="3.5" fill="#FFFFFF" fillOpacity="0.9" stroke="none" />
        </g>
      </motion.g>

      {/* ── Analytics panel (front) ── */}
      <motion.g
        transform="translate(232 286)"
        animate={{ y: [0, -4, 0] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut", delay: 1 }}
      >
        <path d="M0 22 L48 0 L96 22 L48 44 Z" fill="url(#ias-panel)" stroke="var(--color-line)" />
        {[
          { x: 26, h: 8 }, { x: 40, h: 14 }, { x: 54, h: 10 }, { x: 68, h: 18 },
        ].map((b, i) => (
          <motion.rect
            key={i}
            x={b.x} y={22 - b.h / 2} width="6" height={b.h}
            rx="1.5"
            fill={i === 3 ? "var(--color-ai-solid)" : "var(--color-brand)"}
            fillOpacity="0.7"
            animate={{ scaleY: [0.7, 1, 0.7] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: i * 0.3 }}
            style={{ transformOrigin: `${b.x + 3}px 22px` }}
          />
        ))}
      </motion.g>
    </svg>
  );
}
