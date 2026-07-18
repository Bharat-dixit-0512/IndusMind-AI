"use client";

import * as React from "react";
import { motion, animate, useReducedMotion } from "framer-motion";
import { DURATION, EASE } from "@/components/motion/variants";
import { cn } from "@/lib/utils";
import type { Tone } from "./Badge";

/**
 * Counts up to `value` on mount.
 *
 * The count-up is an *enhancement only* — the real figure is always the source
 * of truth. If motion is reduced or the animation is interrupted we snap
 * straight to `value`, because a KPI that displays a stale "0" while animating
 * (or never animates) would be showing the user a number that is simply wrong.
 */
function AnimatedNumber({ value }: { value: number }) {
  const reduceMotion = useReducedMotion();
  // React state, not a MotionValue rendered as a motion child: the latter is
  // server-rendered as its *initial* text and the subscription does not reliably
  // re-attach after hydration, which strands a permanent "0" in the DOM.
  const [shown, setShown] = React.useState(value);

  React.useEffect(() => {
    // Driving an external animation system is exactly what effects are for.
    // State already holds the true figure, so the no-animation path (reduced
    // motion, throttled rAF, background tab) fails safe to the correct number
    // rather than a stale zero. The count-up only ever overwrites it downward
    // on the first frame and restores it on completion.
    if (reduceMotion) return;
    const controls = animate(0, value, {
      duration: DURATION.slow,
      ease: EASE,
      onUpdate: (v) => setShown(Math.round(v)),
      onComplete: () => setShown(value),
    });
    return () => {
      controls.stop();
      setShown(value); // never leave a half-counted, incorrect figure on screen
    };
  }, [value, reduceMotion]);

  return <>{shown.toLocaleString()}</>;
}

const ACCENT: Record<Tone, string> = {
  neutral: "text-ink-tertiary",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  info: "text-info",
  brand: "text-brand",
};

export interface KpiTileProps {
  label: string;
  /**
   * The metric. `null` means "not derivable from the uploaded documents" and
   * renders an em dash — we never substitute a zero or an invented figure.
   */
  value: number | null;
  sub?: string;
  icon?: React.ElementType;
  tone?: Tone;
  className?: string;
}

/**
 * Compact KPI tile for executive overviews. Dense by design: label, figure and
 * one line of context — no oversized empty padding.
 */
export function KpiTile({
  label,
  value,
  sub,
  icon: Icon,
  tone = "neutral",
  className,
}: KpiTileProps) {
  return (
    <motion.div
      // Perceptible hover response: lift + elevation, not just a border tint.
      whileHover={{ y: -4 }}
      transition={{ duration: DURATION.fast, ease: EASE }}
      className={cn(
        // h-full so tiles in a row match height regardless of whether they carry
        // a `sub` line — the grid stretches the wrapper, but without this the
        // tile shrinks to its own content and the row looks ragged.
        "group h-full rounded-ui-xl border border-line bg-surface p-4 shadow-e2",
        "transition-[box-shadow,border-color] duration-200 hover:border-brand-line hover:shadow-e3",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-bold uppercase tracking-wider text-ink-tertiary">
          {label}
        </p>
        {Icon && <Icon className={cn("h-3.5 w-3.5", ACCENT[tone])} />}
      </div>

      <p className="mt-2.5 text-2xl font-bold tabular-nums tracking-tight text-ink">
        {value === null ? (
          <span className="text-ink-tertiary">—</span>
        ) : (
          <AnimatedNumber value={value} />
        )}
      </p>

      {sub && <p className="mt-1 text-[11px] font-medium text-ink-tertiary">{sub}</p>}
    </motion.div>
  );
}
