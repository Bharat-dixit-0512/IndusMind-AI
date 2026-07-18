import type { Variants, Transition } from "framer-motion";

/**
 * Shared motion language.
 *
 * Enterprise motion is *informational*, not decorative: short durations, a
 * single decelerating curve, small travel distances. Every page imports these
 * instead of hand-tuning timings, so the whole app moves as one product.
 */

// Decelerate curve (matches --ease-enterprise in globals.css).
export const EASE: Transition["ease"] = [0.22, 1, 0.36, 1];

/**
 * Durations are deliberately *perceptible*. An earlier pass used 0.15–0.25s
 * with 8px travel, which is technically animated but finishes before the eye
 * registers it — motion that can't be seen may as well not exist.
 */
export const DURATION = {
  fast: 0.2,
  base: 0.38,
  slow: 0.6,
} as const;

/** Page-level fade+lift. Paired with PageTransition. */
export const pageVariants: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.base, ease: EASE },
  },
};

/** Parent list/grid — staggers children in sequence. */
export const staggerContainer: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.07, delayChildren: 0.06 },
  },
};

/** Child of staggerContainer (cards, rows, KPI tiles). */
export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.base, ease: EASE },
  },
};

/** Simple fade — for text/secondary content. */
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: DURATION.base, ease: EASE } },
};

/** Height auto expand/collapse (accordions, detail panels). */
export const expandCollapse: Variants = {
  collapsed: { height: 0, opacity: 0 },
  expanded: {
    height: "auto",
    opacity: 1,
    transition: { duration: DURATION.base, ease: EASE },
  },
};

/**
 * Hover lift for interactive surfaces. Spread onto a motion component:
 *   <motion.div {...hoverLift}>
 * (Card exposes an `interactive` prop that does the CSS equivalent for
 * non-motion surfaces.)
 */
export const hoverLift = {
  whileHover: { y: -3 },
  transition: { duration: DURATION.fast, ease: EASE },
} as const;
