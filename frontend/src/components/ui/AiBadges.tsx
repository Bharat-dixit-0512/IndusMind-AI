import * as React from "react";
import { FileText, Sparkles, ShieldCheck, Gauge } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Provenance vocabulary for AI-derived content.
 *
 * Purple is reserved system-wide for "this was produced or scored by the AI".
 * Because the platform's whole premise is grounded output, these badges are how
 * a reader tells at a glance *what* an assertion rests on — they should sit on
 * every AI-generated section.
 */

const base =
  "inline-flex items-center gap-1 rounded-ui-sm border px-1.5 py-0.5 text-[11px] font-semibold whitespace-nowrap";

/** Marks a block as machine-generated rather than quoted from a document. */
export function AiGeneratedBadge({ className }: { className?: string }) {
  return (
    <span className={cn(base, "border-ai-line bg-ai-subtle text-ai", className)}>
      <Sparkles className="h-3 w-3" /> AI generated
    </span>
  );
}

/** Model/pipeline confidence for this specific answer (0–1). */
export function ConfidenceBadge({ score, className }: { score: number; className?: string }) {
  const pct = Math.round(score * 100);
  // Confidence is a quality signal, so it uses status tones, not brand purple.
  const tone =
    pct >= 90 ? "border-success/25 bg-success-subtle text-success"
    : pct >= 75 ? "border-ai-line bg-ai-subtle text-ai"
    : pct >= 60 ? "border-warning/25 bg-warning-subtle text-warning"
    : "border-danger/25 bg-danger-subtle text-danger";
  return (
    <span className={cn(base, tone, className)}>
      <Gauge className="h-3 w-3" /> {pct}% confidence
    </span>
  );
}

/** How many evidence snippets back the statement. */
export function EvidenceBadge({ count, className }: { count: number; className?: string }) {
  return (
    <span className={cn(base, "border-line bg-subtle text-ink-secondary", className)}>
      <ShieldCheck className="h-3 w-3" /> {count} evidence
    </span>
  );
}

/** The originating document. */
export function SourceBadge({ name, page, className }: { name: string; page?: number | null; className?: string }) {
  return (
    <span
      className={cn(base, "border-line bg-surface text-ink-secondary max-w-[220px]", className)}
      title={name}
    >
      <FileText className="h-3 w-3 shrink-0" />
      <span className="truncate">{name}{page != null ? ` · p.${page}` : ""}</span>
    </span>
  );
}
