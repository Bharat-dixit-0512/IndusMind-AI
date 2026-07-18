"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle, BarChart3, Download, FileSearch, FileText, Plus,
  RefreshCw, Search, ShieldCheck, Wrench, X,
} from "lucide-react";

import {
  downloadReportFile, generateReport, listReports, type ReportRecord,
} from "@/lib/api";
import PageTransition from "@/components/motion/PageTransition";
import { staggerContainer, staggerItem } from "@/components/motion/variants";
import {
  Badge, Button, Card, CardContent, CardHeader, CardTitle, Dialog, EmptyState,
  Skeleton, type Tone,
} from "@/components/ui";
import { cn } from "@/lib/utils";

/* Report metadata (title, type, timestamp, author) is real. The API does not
   track downloads, so this page shows *generation* history — it never invents
   download counts, and never fabricates a per-report status. */

const REPORT_TYPES = [
  { value: "RCA", label: "Root cause analysis", icon: Wrench, tone: "danger" as Tone },
  { value: "COMPLIANCE", label: "Compliance audit", icon: ShieldCheck, tone: "brand" as Tone },
  { value: "MAINTENANCE", label: "Maintenance report", icon: Wrench, tone: "success" as Tone },
  { value: "INSPECTION", label: "Inspection summary", icon: FileSearch, tone: "warning" as Tone },
  { value: "EXECUTIVE", label: "Executive summary", icon: BarChart3, tone: "info" as Tone },
] as const;

const TYPE_MAP = Object.fromEntries(REPORT_TYPES.map((t) => [t.value, t])) as Record<
  string,
  (typeof REPORT_TYPES)[number]
>;

function formatDate(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState<string>("RCA");
  const [generating, setGenerating] = useState(false);

  const [filter, setFilter] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const refresh = useCallback(() => { setLoading(true); setReloadKey((k) => k + 1); }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await listReports();
        if (!alive) return;
        setReports(r); setLoadError(null);
      } catch {
        if (alive) setLoadError("Couldn't reach the reports service.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [reloadKey]);

  const handleGenerate = async () => {
    if (!newTitle.trim()) return;
    setGenerating(true);
    setError("");
    try {
      // No simulated pipeline: the spinner reflects the real request duration.
      const report = await generateReport(newTitle.trim(), newType);
      setReports((r) => [report, ...r]);
      setDialogOpen(false);
      setNewTitle("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (r: ReportRecord) => {
    setDownloadingId(r.id);
    setError("");
    try {
      await downloadReportFile(r.id, `${r.title || "report"}.pdf`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloadingId(null);
    }
  };

  const counts = useMemo(
    () => REPORT_TYPES.map((t) => ({ ...t, count: reports.filter((r) => r.report_type === t.value).length })),
    [reports]
  );

  const visible = useMemo(() => {
    const pool = filter ? reports.filter((r) => r.report_type === filter) : reports;
    const q = query.trim().toLowerCase();
    return q ? pool.filter((r) => (r.title ?? "").toLowerCase().includes(q)) : pool;
  }, [reports, filter, query]);

  return (
    <PageTransition className="space-y-4 p-5 md:p-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="t-page text-ink">Reports</h1>
          <p className="mt-0.5 text-xs text-ink-secondary">
            Grounded PDFs compiled from your documents — every report cites its sources.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="primary" size="sm" onClick={() => setDialogOpen(true)}>
            <Plus className="h-3.5 w-3.5" /> New report
          </Button>
          <Button size="sm" onClick={refresh} disabled={loading}>
            <RefreshCw className={loading ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"} /> Refresh
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-danger/30 bg-danger-subtle">
          <CardContent className="flex items-center gap-2.5 py-2.5">
            <AlertTriangle className="h-4 w-4 shrink-0 text-danger" />
            <p className="flex-1 text-xs font-medium text-danger">{error}</p>
            <button onClick={() => setError("")} className="text-danger/70 hover:text-danger">
              <X className="h-3.5 w-3.5" />
            </button>
          </CardContent>
        </Card>
      )}

      {/* Type summary */}
      {!loadError && (
        <motion.div variants={staggerContainer} initial="hidden" animate="show"
          className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {counts.map((t) => {
            const Icon = t.icon;
            const active = filter === t.value;
            return (
              <motion.button
                key={t.value}
                variants={staggerItem}
                onClick={() => setFilter(active ? null : t.value)}
                className={cn(
                  "rounded-ui-xl border bg-surface p-3 text-left shadow-e1 transition-colors",
                  active ? "border-brand-line bg-brand-subtle" : "border-line hover:border-line-strong"
                )}
              >
                <div className="flex items-center justify-between">
                  <Icon className={cn("h-3.5 w-3.5", active ? "text-brand" : "text-ink-tertiary")} />
                  <span className="text-lg font-bold tabular-nums text-ink">
                    {loading ? "—" : t.count}
                  </span>
                </div>
                <p className="mt-1 text-[11px] font-semibold leading-tight text-ink-secondary">{t.label}</p>
              </motion.button>
            );
          })}
        </motion.div>
      )}

      {/* Library */}
      <Card>
        <CardHeader className="flex-col items-stretch gap-2.5 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <CardTitle>Report library</CardTitle>
            {!loadError && !loading && (
              <span className="text-[11px] text-ink-tertiary">
                {visible.length}{filter ? ` of ${reports.length}` : ""}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 sm:ml-auto">
            {filter && (
              <Button size="sm" onClick={() => setFilter(null)}>
                <X className="h-3 w-3" /> Clear filter
              </Button>
            )}
            <div className="relative w-56">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-tertiary" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search reports…"
                className="w-full rounded-ui-md border border-line bg-canvas py-1.5 pl-8 pr-3 text-xs text-ink outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {loading ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
            </div>
          ) : loadError ? (
            <EmptyState
              icon={AlertTriangle}
              title="Library unavailable"
              reason="The reports service couldn't be reached, so your reports can't be listed. This does not mean you have none."
              action={<Button size="sm" onClick={refresh}>Retry</Button>}
            />
          ) : reports.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No reports yet"
              reason="Reports are compiled from your uploaded documents — each one cites the sources it drew from."
              hint="Generate your first report to see it here."
              action={
                <Button variant="primary" size="sm" onClick={() => setDialogOpen(true)}>
                  <Plus className="h-3.5 w-3.5" /> New report
                </Button>
              }
            />
          ) : visible.length === 0 ? (
            <EmptyState
              icon={Search}
              title="No matching reports"
              reason="No report matches the current filter or search term."
              action={<Button size="sm" onClick={() => { setFilter(null); setQuery(""); }}>Reset</Button>}
            />
          ) : (
            <motion.ul variants={staggerContainer} initial="hidden" animate="show" className="divide-y divide-line">
              {visible.map((r) => {
                const meta = TYPE_MAP[r.report_type];
                const Icon = meta?.icon ?? FileText;
                return (
                  <motion.li
                    key={r.id}
                    variants={staggerItem}
                    className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-subtle"
                  >
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-ui-md border border-line bg-subtle">
                      <Icon className="h-4 w-4 text-ink-secondary" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-bold text-ink" title={r.title}>
                        {r.title}
                      </p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-ink-tertiary">
                        <Badge tone={meta?.tone ?? "neutral"}>{r.report_type}</Badge>
                        <span>Generated {formatDate(r.created_at)}</span>
                      </p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleDownload(r)}
                      loading={downloadingId === r.id}
                    >
                      <Download className="h-3.5 w-3.5" /> PDF
                    </Button>
                  </motion.li>
                );
              })}
            </motion.ul>
          )}
        </CardContent>
      </Card>

      {/* Generate dialog */}
      <Dialog
        open={dialogOpen}
        onOpenChange={(o) => { if (!generating) setDialogOpen(o); }}
        title="Generate report"
        description="The report is compiled from your uploaded documents. If nothing relevant is found, it will say so rather than invent content."
        footer={
          <>
            <Button size="sm" onClick={() => setDialogOpen(false)} disabled={generating}>Cancel</Button>
            <Button
              size="sm"
              variant="primary"
              onClick={handleGenerate}
              loading={generating}
              disabled={!newTitle.trim()}
            >
              Generate
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label htmlFor="report-title" className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-ink-tertiary">
              Title
            </label>
            <input
              id="report-title"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. Q3 compressor failure review"
              className="w-full rounded-ui-md border border-line bg-canvas px-3 py-2 text-[13px] text-ink outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
            />
          </div>
          <div>
            <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-tertiary">Type</p>
            <div className="grid grid-cols-2 gap-1.5">
              {REPORT_TYPES.map((t) => {
                const Icon = t.icon;
                const active = newType === t.value;
                return (
                  <button
                    key={t.value}
                    onClick={() => setNewType(t.value)}
                    className={cn(
                      "flex items-center gap-2 rounded-ui-md border px-2.5 py-2 text-left transition-colors",
                      active
                        ? "border-brand-line bg-brand-subtle text-brand"
                        : "border-line bg-surface text-ink-secondary hover:bg-subtle"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0" />
                    <span className="text-[11px] font-semibold leading-tight">{t.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </Dialog>
    </PageTransition>
  );
}
