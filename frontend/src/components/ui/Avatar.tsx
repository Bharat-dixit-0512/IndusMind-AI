"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Derives display initials from a name, falling back to the email local part.
 *
 * "Abhishek Sharma" -> AS   ·   "Abhishek" -> A   ·   "a.sharma@corp.com" -> AS
 *
 * Punctuation in email locals ("a.sharma", "a_sharma", "a-sharma") is treated as
 * a word break, which is what makes the email fallback produce something
 * meaningful instead of a single letter.
 */
export function initialsFrom(name?: string | null, email?: string | null): string {
  const fromName = (name ?? "").trim();
  const fromEmail = (email ?? "").split("@")[0].replace(/[._\-+]+/g, " ").trim();
  const source = fromName || fromEmail;
  if (!source) return "?";

  const words = source.split(/\s+/).filter(Boolean);
  const first = words[0]?.[0] ?? "";
  const last = words.length > 1 ? words[words.length - 1][0] : "";
  return (first + last).toUpperCase();
}

const SIZE = {
  sm: "h-7 w-7 text-[10px]",
  md: "h-8 w-8 text-[11px]",
  lg: "h-11 w-11 text-sm",
} as const;

export interface AvatarProps {
  name?: string | null;
  email?: string | null;
  size?: keyof typeof SIZE;
  className?: string;
}

/**
 * Initials avatar.
 *
 * Deliberately not a presence indicator: the app has no real connectivity
 * signal for a user, and a dot that is always green would be decoration
 * pretending to be status.
 */
export function Avatar({ name, email, size = "md", className }: AvatarProps) {
  const initials = initialsFrom(name, email);
  const label = name?.trim() || email?.trim() || "Account";

  return (
    <span
      role="img"
      aria-label={label}
      title={label}
      className={cn(
        "relative inline-flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full",
        "bg-gradient-to-br from-brand to-ai-solid font-bold uppercase leading-none tracking-wide text-white",
        // Hairline ring separates the avatar from the dark sidebar without a
        // hard border, and the drop shadow seats it on the surface.
        "ring-1 ring-inset ring-white/20 shadow-[0_2px_8px_-2px_rgba(15,23,42,0.5)]",
        SIZE[size],
        className
      )}
    >
      {/* Top-down highlight: reads as a lit sphere rather than a flat disc. */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white/25 via-transparent to-black/10"
      />
      <span className="relative">{initials}</span>
    </span>
  );
}
