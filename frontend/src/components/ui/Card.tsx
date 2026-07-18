import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * The enterprise card: flat white surface, 1px hairline border, minimal
 * elevation. No glass, no gradient, no glow — depth comes from the border and a
 * single low-alpha shadow, the way Stripe/Linear panels read.
 */
export function Card({
  className,
  interactive = false,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  /** Adds a hover lift + elevation. Use for clickable/navigable cards. */
  interactive?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-ui-xl border border-line bg-surface shadow-e2",
        interactive &&
          "cursor-pointer transition-[transform,box-shadow,border-color] duration-200 " +
            "hover:-translate-y-1 hover:border-brand-line hover:shadow-e3",
        className
      )}
      {...props}
    />
  );
}

/** Card header row — title/description on the left, actions on the right. */
export function CardHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-3 border-b border-line px-5 py-3.5",
        className
      )}
      {...props}
    />
  );
}

export function CardTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn(
        "text-[11px] font-bold uppercase tracking-wider text-ink-tertiary",
        className
      )}
      {...props}
    />
  );
}

export function CardContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5", className)} {...props} />;
}
