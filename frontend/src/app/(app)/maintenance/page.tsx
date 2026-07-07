"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchMaintenanceOverview, fetchAssetDetail, generateReport, getReportDownloadUrl,
  type MaintenanceOverview, type MaintenanceAsset, type AssetDetail, type Citation, type TimelineEvent,
} from "@/lib/api";
import {
  Wrench, Loader2, CheckCircle2, ChevronDown, ChevronUp, Download, FileText, Clock,
  AlertTriangle, Zap, RotateCcw, CheckCheck, Cpu, Package, User as UserIcon, MapPin,
  Sparkles, Boxes, RefreshCw,
} from "lucide-react";

// ─── Timeline Status Config ─────────────────────────────────────────────────
const TIMELINE_STATUS: Record<string, { color: string; bg: string; glow: string; Icon: React.ElementType; label: string }> = {
  normal:  { color: "#10b981", bg: "rgba(16,185,129,0.12)",  glow: "rgba(16,185,129,0.3)",  Icon: CheckCheck,    label: "Normal"   },
  warning: { color: "#f59e0b", bg: "rgba(245,158,11,0.12)",  glow: "rgba(245,158,11,0.3)",  Icon: AlertTriangle, label: "Warning"  },
  ignored: { color: "#64748b", bg: "rgba(100,116,139,0.12)", glow: "rgba(100,116,139,0.2)", Icon: Clock,         label: "Ignored"  },
  failure: { color: "#ef4444", bg: "rgba(239,68,68,0.12)",   glow: "rgba(239,68,68,0.3)",   Icon: Zap,           label: "Critical" },
  repair:  { color: "#3b82f6", bg: "rgba(59,130,246,0.12)",  glow: "rgba(59,130,246,0.3)",  Icon: RotateCcw,     label: "Repair"   },
};

// Icon + color per discovered asset type.
const ASSET_META: Record<string, { Icon: React.ElementType; color: string }> = {
  Machine:           { Icon: Cpu,      color: "#3b82f6" },
  Equipment:         { Icon: Cpu,      color: "#3b82f6" },
  SparePart:         { Icon: Package,  color: "#f97316" },
  Engineer:          { Icon: UserIcon, color: "#6366f1" },
  Location:          { Icon: MapPin,   color: "#14b8a6" },
  Failure:           { Icon: Zap,      color: "#ef4444" },
  MaintenanceRecord: { Icon: Wrench,   color: "#10b981" },
  InspectionReport:  { Icon: FileText, color: "#f59e0b" },
  SOP:               { Icon: FileText, color: "#8b5cf6" },
};

function FailureTimeline({ events }: { events: TimelineEvent[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0);
  return (
    <div className="glass-card rounded-xl p-5">
      <p className="text-xs font-semibold mb-5" style={{ color: "#f59e0b" }}>⏱ Failure Chronology Timeline</p>
      <div className="relative">
        <div className="absolute left-[19px] top-5 bottom-5 w-px" style={{ background: "linear-gradient(to bottom, rgba(59,130,246,0.3), rgba(239,68,68,0.4), rgba(59,130,246,0.3))" }} />
        <div className="space-y-0">
          {events.map((evt, i) => {
            const cfg = TIMELINE_STATUS[evt.status] ?? TIMELINE_STATUS.normal;
            const Icon = cfg.Icon;
            const isExpanded = expandedIdx === i;
            const isLast = i === events.length - 1;
            return (
              <div key={i} className={`relative flex gap-4 ${isLast ? "" : "pb-1"}`}>
                <div className="flex-shrink-0 w-10 flex flex-col items-center">
                  <button onClick={() => setExpandedIdx(isExpanded ? null : i)}
                    className="w-10 h-10 rounded-full flex items-center justify-center z-10 transition-all duration-200 hover:scale-110"
                    style={{ background: cfg.bg, border: `2px solid ${cfg.color}`, boxShadow: `0 0 12px ${cfg.glow}` }}>
                    <Icon className="w-4 h-4" style={{ color: cfg.color }} />
                  </button>
                </div>
                <div className="flex-1 pb-6">
                  <button className="w-full text-left" onClick={() => setExpandedIdx(isExpanded ? null : i)}>
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}40` }}>{cfg.label}</span>
                      <span className="text-xs font-mono text-slate-500">{evt.time}</span>
                    </div>
                    <p className="text-sm font-semibold text-slate-200">{evt.event}</p>
                  </button>
                  <div className="overflow-hidden transition-all duration-300" style={{ maxHeight: isExpanded ? "200px" : "0", opacity: isExpanded ? 1 : 0 }}>
                    <div className="mt-2 px-3 py-2.5 rounded-lg text-xs text-slate-400 leading-relaxed" style={{ background: cfg.bg, borderLeft: `3px solid ${cfg.color}` }}>{evt.detail}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Section({ title, items, color = "#3b82f6" }: { title: string; items: string[]; color?: string }) {
  const [open, setOpen] = useState(true);
  if (!items || items.length === 0) return null;
  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors">
        <span className="text-xs font-semibold" style={{ color }}>{title}</span>
        {open ? <ChevronUp className="w-3.5 h-3.5 text-slate-500" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-500" />}
      </button>
      {open && (
        <div className="px-4 pb-3 space-y-1.5">
          {items.map((item, i) => (
            <div key={i} className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ background: color }} />
              <p className="text-xs text-slate-400 leading-relaxed">{item}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MaintenancePage() {
  const [overview, setOverview] = useState<MaintenanceOverview | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<AssetDetail | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);

  const loadOverview = useCallback(() => {
    setLoadingOverview(true);
    fetchMaintenanceOverview()
      .then(setOverview)
      .catch(console.error)
      .finally(() => setLoadingOverview(false));
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount, not derived render state
    loadOverview();
  }, [loadOverview]);

  const analyzeAsset = async (assetName: string) => {
    setSelected(assetName);
    setAnalyzing(true);
    setDetail(null);
    try {
      setDetail(await fetchAssetDetail(assetName));
    } catch (e) { console.error(e); }
    finally { setAnalyzing(false); }
  };

  const downloadRca = async () => {
    if (!selected) return;
    setGenerating(true);
    try {
      const report = await generateReport(`RCA – ${selected}`, "RCA");
      window.open(getReportDownloadUrl(report.id), "_blank");
    } catch (e) { console.error(e); }
    finally { setGenerating(false); }
  };

  const rca = detail?.report;
  const citations: Citation[] = detail?.citations ?? [];
  const timelineEvents: TimelineEvent[] = rca?.timeline ?? [];

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-start justify-between mb-6 gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "linear-gradient(135deg, #10b981, #059669)" }}>
              <Wrench className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">Maintenance Intelligence</h1>
          </div>
          <p className="text-sm text-slate-500 ml-11">Assets and incidents auto-discovered from your uploaded documents. Click any asset for a Root Cause Analysis.</p>
        </div>
        <button onClick={loadOverview} className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-slate-300 flex-shrink-0 transition-all" style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {loadingOverview ? (
        <div className="glass-card rounded-2xl p-10 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
        </div>
      ) : !overview?.has_data ? (
        <div className="glass-card rounded-2xl p-10 text-center">
          <Boxes className="w-8 h-8 mx-auto mb-3 text-slate-700" />
          <p className="text-sm text-slate-400">No maintenance data yet</p>
          <p className="text-xs text-slate-600 mt-1 max-w-md mx-auto">{overview?.message}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          {/* Left: discovery + analysis */}
          <div className="xl:col-span-2 space-y-4">
            {/* Discovered assets */}
            <div className="glass-card rounded-2xl p-5">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-slate-300">Discovered Assets</p>
                <span className="text-xs text-slate-600">{overview.assets.length} found</span>
              </div>
              {overview.assets.length === 0 ? (
                <p className="text-xs text-slate-600">No named assets extracted yet — try uploading machine manuals or work orders.</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {overview.assets.map((a: MaintenanceAsset) => {
                    const meta = ASSET_META[a.type] ?? { Icon: Cpu, color: "#64748b" };
                    const Icon = meta.Icon;
                    const active = selected === a.name;
                    return (
                      <button key={a.id} onClick={() => analyzeAsset(a.name)}
                        className="flex items-start gap-2.5 p-3 rounded-xl text-left transition-all hover:scale-[1.02]"
                        style={{ background: active ? `${meta.color}18` : "rgba(255,255,255,0.03)", border: `1px solid ${active ? `${meta.color}55` : "rgba(255,255,255,0.07)"}` }}>
                        <Icon className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: meta.color }} />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-slate-200 truncate">{a.name}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5">{a.type} · {a.doc_count} doc{a.doc_count === 1 ? "" : "s"}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Analysis result */}
            {analyzing && (
              <div className="glass-card rounded-2xl p-8 flex items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-emerald-400" />
                <span className="text-sm text-slate-400">Analysing {selected}…</span>
              </div>
            )}

            {rca && !analyzing && (
              <>
                <div className="glass-card rounded-2xl p-5">
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span className="text-xs text-emerald-400 font-medium">Analysis Complete</span>
                      </div>
                      <h2 className="text-lg font-bold text-slate-100">Asset: {rca.equipment_id || selected}</h2>
                      <p className="text-sm text-red-400 mt-1">{rca.failure_mode}</p>
                    </div>
                    <button onClick={downloadRca} disabled={generating}
                      className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-slate-300 transition-all flex-shrink-0"
                      style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
                      {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                      Export PDF
                    </button>
                  </div>
                  <div className="p-4 rounded-xl" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)" }}>
                    <p className="text-xs font-semibold text-red-400 mb-2">Root Cause</p>
                    <p className="text-sm text-slate-300 leading-relaxed">{rca.root_cause}</p>
                  </div>
                </div>

                {timelineEvents.length > 0 && <FailureTimeline events={timelineEvents} />}
                <Section title="Maintenance Actions Taken" items={rca.maintenance_actions_taken} color="#10b981" />
                <Section title="Lessons Learned" items={rca.lessons_learned} color="#6366f1" />
              </>
            )}

            {!selected && !analyzing && (
              <div className="glass-card rounded-2xl p-8 text-center">
                <Wrench className="w-7 h-7 mx-auto mb-2 text-slate-700" />
                <p className="text-sm text-slate-500">Select a discovered asset above to generate its Root Cause Analysis.</p>
              </div>
            )}
          </div>

          {/* Right: context from the knowledge base */}
          <div className="space-y-4">
            {rca && <Section title="Preventive Recommendations" items={rca.preventive_recommendations} color="#3b82f6" />}

            {citations.length > 0 && (
              <div className="glass-card rounded-2xl p-4">
                <p className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-2"><FileText className="w-3.5 h-3.5" /> Sources Used</p>
                <div className="space-y-2">
                  {citations.map((c, i) => (
                    <div key={i} className="px-3 py-2 rounded-lg" style={{ background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.12)" }}>
                      <p className="text-xs font-medium text-blue-300 truncate">{c.document_name}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {overview.recent_incidents.length > 0 && (
              <div className="glass-card rounded-2xl p-4">
                <p className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-2"><AlertTriangle className="w-3.5 h-3.5 text-red-400" /> Recent Incidents</p>
                <div className="space-y-2">
                  {overview.recent_incidents.map(d => (
                    <div key={d.id} className="px-3 py-2 rounded-lg" style={{ background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.12)" }}>
                      <p className="text-xs font-medium text-slate-300 truncate">{d.filename}</p>
                      <p className="text-[10px] text-slate-600 mt-0.5">{d.category}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {overview.recurring_patterns.length > 0 && (
              <div className="glass-card rounded-2xl p-4">
                <p className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-2"><Sparkles className="w-3.5 h-3.5 text-amber-400" /> Recurring Assets</p>
                <div className="space-y-2">
                  {overview.recurring_patterns.map((p, i) => (
                    <div key={i} className="px-3 py-2 rounded-lg" style={{ background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.12)" }}>
                      <p className="text-xs font-medium text-slate-300 truncate">{p.name}</p>
                      <p className="text-[10px] text-slate-600 mt-0.5">{p.type} · in {p.doc_count} documents</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {rca?.confidence_score != null && (
              <div className="glass-card rounded-2xl p-4">
                <p className="text-xs font-semibold text-slate-400 mb-3">AI Confidence</p>
                <div className="flex items-end gap-2">
                  <p className="text-3xl font-bold" style={{ color: "#10b981" }}>{Math.round(rca.confidence_score * 100)}%</p>
                  <p className="text-xs text-slate-600 mb-1">grounding</p>
                </div>
                <div className="mt-2 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                  <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${Math.round(rca.confidence_score * 100)}%`, background: "linear-gradient(90deg, #10b981, #3b82f6)" }} />
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
