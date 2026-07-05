"use client";

import { useState } from "react";
import { sendChatMessage, generateReport, getReportDownloadUrl, type ChatResponse, type TimelineEvent } from "@/lib/api";
import { Wrench, Loader2, CheckCircle2, ChevronDown, ChevronUp, Download, FileText, Clock, AlertTriangle, Zap, RotateCcw, CheckCheck } from "lucide-react";

const ASSET_OPTIONS = ["P-102 Centrifugal Pump", "C-301 Reciprocating Compressor", "T-502 Turbine", "All Train 2 Assets"];

interface RcaData {
  equipment_id: string;
  failure_mode: string;
  chronology: string[];
  timeline?: TimelineEvent[];
  root_cause: string;
  maintenance_actions_taken: string[];
  preventive_recommendations: string[];
  lessons_learned: string[];
}

// ─── Timeline Status Config ─────────────────────────────────────────────────
const TIMELINE_STATUS: Record<string, { color: string; bg: string; glow: string; Icon: React.ElementType; label: string }> = {
  normal:  { color: "#10b981", bg: "rgba(16,185,129,0.12)",  glow: "rgba(16,185,129,0.3)",  Icon: CheckCheck,    label: "Normal"   },
  warning: { color: "#f59e0b", bg: "rgba(245,158,11,0.12)",  glow: "rgba(245,158,11,0.3)",  Icon: AlertTriangle, label: "Warning"  },
  ignored: { color: "#64748b", bg: "rgba(100,116,139,0.12)", glow: "rgba(100,116,139,0.2)", Icon: Clock,         label: "Ignored"  },
  failure: { color: "#ef4444", bg: "rgba(239,68,68,0.12)",   glow: "rgba(239,68,68,0.3)",   Icon: Zap,           label: "Critical" },
  repair:  { color: "#3b82f6", bg: "rgba(59,130,246,0.12)",  glow: "rgba(59,130,246,0.3)",  Icon: RotateCcw,     label: "Repair"   },
};

// ─── Vertical Timeline Component ─────────────────────────────────────────────
function FailureTimeline({ events }: { events: TimelineEvent[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0);

  return (
    <div className="glass-card rounded-xl p-5">
      <p className="text-xs font-semibold mb-5" style={{ color: "#f59e0b" }}>
        ⏱ Failure Chronology Timeline
      </p>
      <div className="relative">
        {/* Vertical connecting line */}
        <div
          className="absolute left-[19px] top-5 bottom-5 w-px"
          style={{ background: "linear-gradient(to bottom, rgba(59,130,246,0.3), rgba(239,68,68,0.4), rgba(59,130,246,0.3))" }}
        />

        <div className="space-y-0">
          {events.map((evt, i) => {
            const cfg = TIMELINE_STATUS[evt.status] ?? TIMELINE_STATUS.normal;
            const Icon = cfg.Icon;
            const isExpanded = expandedIdx === i;
            const isLast = i === events.length - 1;

            return (
              <div key={i} className={`relative flex gap-4 ${isLast ? "" : "pb-1"}`}>
                {/* Dot + icon */}
                <div className="flex-shrink-0 w-10 flex flex-col items-center">
                  <button
                    onClick={() => setExpandedIdx(isExpanded ? null : i)}
                    className="w-10 h-10 rounded-full flex items-center justify-center z-10 transition-all duration-200 hover:scale-110"
                    style={{
                      background: cfg.bg,
                      border: `2px solid ${cfg.color}`,
                      boxShadow: `0 0 12px ${cfg.glow}`,
                    }}
                  >
                    <Icon className="w-4 h-4" style={{ color: cfg.color }} />
                  </button>
                </div>

                {/* Content card */}
                <div className="flex-1 pb-6">
                  <button
                    className="w-full text-left"
                    onClick={() => setExpandedIdx(isExpanded ? null : i)}
                  >
                    <div className="flex items-center gap-3 mb-1">
                      <span
                        className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                        style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}40` }}
                      >
                        {cfg.label}
                      </span>
                      <span className="text-xs font-mono text-slate-500">{evt.time}</span>
                    </div>
                    <p className="text-sm font-semibold text-slate-200">{evt.event}</p>
                  </button>

                  {/* Expandable detail */}
                  <div
                    className="overflow-hidden transition-all duration-300"
                    style={{ maxHeight: isExpanded ? "200px" : "0", opacity: isExpanded ? 1 : 0 }}
                  >
                    <div
                      className="mt-2 px-3 py-2.5 rounded-lg text-xs text-slate-400 leading-relaxed"
                      style={{ background: cfg.bg, borderLeft: `3px solid ${cfg.color}` }}
                    >
                      {evt.detail}
                    </div>
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

// ─── Collapsible Section ─────────────────────────────────────────────────────
function Section({ title, items, color = "#3b82f6" }: { title: string; items: string[]; color?: string }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
      >
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

// ─── Static mock RCA ─────────────────────────────────────────────────────────
const MOCK_RCA: RcaData = {
  equipment_id: "P-102",
  failure_mode: "Mechanical Seal Rupture due to High Shaft Vibration",
  chronology: [
    "2026-05-08: Pre-operational inspection — vibration within normal limits (1.8 mm/s RMS).",
    "2026-05-12: Operator logs note a slight hum and leakage rate at ~5 drops/min.",
    "2026-05-14: Vibration alarm fires at 4.2 mm/s RMS. Primary seal rupture confirmed. Manual shutdown.",
  ],
  timeline: [
    { time: "2026-05-08", event: "Baseline Sweep", status: "normal",  detail: "Radial vibration within normal limits (1.8 mm/s RMS). Pump operating nominally." },
    { time: "2026-05-12", event: "Hum & Leakage",  status: "warning", detail: "Operator Ahmad Malik noted slight casing hum; mechanical seal leak at 5 drops/min." },
    { time: "2026-05-13", event: "Warning Ignored", status: "ignored", detail: "No corrective alignment scheduled — shift transition delays prevented follow-up inspection." },
    { time: "2026-05-14", event: "Critical Alarm",  status: "failure", detail: "Vibration spikes to 4.2 mm/s RMS. Mechanical Seal S-100 ruptures. Emergency casing shutdown." },
    { time: "2026-05-15", event: "Repair & Restore",status: "repair",  detail: "Seal S-100 & Impeller Kit K-402 replaced. Laser shaft realignment achieved 0.02 mm tolerance." },
  ],
  root_cause: "Shaft misalignment (0.08 mm vs SOP limit of 0.05 mm) introduced during the previous motor decoupling. Dynamic offset stresses caused impeller wobble, bearing wear, and seal face degradation.",
  maintenance_actions_taken: [
    "Pump isolated and lockout/tagout applied.",
    "Impeller casing opened — worn seal faces and bearing clearance found.",
    "Mechanical Seal S-100 replaced.",
    "Impeller Kit K-402 installed.",
    "Laser shaft realignment performed — tolerance achieved: 0.02 mm.",
  ],
  preventive_recommendations: [
    "Mandate post-decoupling laser alignment sign-off by QA.",
    "Increase vibration sweeps from monthly to bi-weekly on Train 2 rotating assets.",
    "Add mechanical seal drip-rate check to operator daily round sheets.",
  ],
  lessons_learned: [
    "Coupling alignment cannot rely on visual or straight-edge methods alone.",
    "Early leakage reports must trigger immediate corrective inspection — not just manual log entries.",
  ],
};

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function MaintenancePage() {
  const [asset, setAsset] = useState(ASSET_OPTIONS[0]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [rca, setRca] = useState<RcaData | null>(null);
  const [rawResponse, setRawResponse] = useState<ChatResponse | null>(null);
  const [generating, setGenerating] = useState(false);

  const runAnalysis = async () => {
    const q = `Generate RCA for ${asset}. ${query}`.trim();
    setLoading(true);
    setRca(null);
    try {
      const res = await sendChatMessage(q);
      setRawResponse(res);
      // Try to parse JSON from response
      const jsonMatch = res.response.match(/```json([\s\S]*?)```|(\{[\s\S]*\})/);
      if (jsonMatch) {
        try { setRca(JSON.parse(jsonMatch[1] ?? jsonMatch[2])); } catch { /* use raw */ }
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const downloadRca = async () => {
    setGenerating(true);
    try {
      const report = await generateReport(`RCA – ${asset}`, "RCA");
      window.open(getReportDownloadUrl(report.id), "_blank");
    } catch (e) { console.error(e); }
    finally { setGenerating(false); }
  };

  const displayRca = rca ?? MOCK_RCA;
  // Use timeline from backend if available, otherwise use mock timeline
  const timelineEvents: TimelineEvent[] =
    (rawResponse?.timeline && rawResponse.timeline.length > 0)
      ? rawResponse.timeline
      : (displayRca.timeline ?? []);

  return (
    <div className="p-8">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "linear-gradient(135deg, #10b981, #059669)" }}>
            <Wrench className="w-4 h-4 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Maintenance Intelligence</h1>
        </div>
        <p className="text-sm text-slate-500 ml-11">AI-generated Root Cause Analysis and preventive recommendations from your plant documents.</p>
      </div>

      {/* Controls */}
      <div className="glass-card rounded-2xl p-5 mb-6">
        <div className="flex gap-3 flex-wrap">
          <select
            value={asset}
            onChange={e => setAsset(e.target.value)}
            className="flex-1 px-4 py-2.5 rounded-xl text-sm text-slate-200 outline-none min-w-48"
            style={{ background: "rgba(15,23,42,0.7)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            {ASSET_OPTIONS.map(a => <option key={a}>{a}</option>)}
          </select>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Additional context (optional)…"
            className="flex-1 px-4 py-2.5 rounded-xl text-sm text-slate-200 placeholder:text-slate-600 outline-none min-w-56"
            style={{ background: "rgba(15,23,42,0.7)", border: "1px solid rgba(255,255,255,0.08)" }}
          />
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-50"
            style={{ background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 4px 12px rgba(16,185,129,0.25)" }}
          >
            {loading ? <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />Analysing…</span> : "Run RCA →"}
          </button>
        </div>
      </div>

      {/* RCA Results */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Left / Main column */}
        <div className="xl:col-span-2 space-y-4">
          {/* Summary card */}
          <div className="glass-card rounded-2xl p-5">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs text-emerald-400 font-medium">Analysis Complete</span>
                </div>
                <h2 className="text-lg font-bold text-slate-100">Asset: {displayRca.equipment_id}</h2>
                <p className="text-sm text-red-400 mt-1">{displayRca.failure_mode}</p>
              </div>
              <button
                onClick={downloadRca}
                disabled={generating}
                className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-slate-300 transition-all flex-shrink-0"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}
              >
                {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                Export PDF
              </button>
            </div>
            <div className="p-4 rounded-xl" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)" }}>
              <p className="text-xs font-semibold text-red-400 mb-2">Root Cause</p>
              <p className="text-sm text-slate-300 leading-relaxed">{displayRca.root_cause}</p>
            </div>
          </div>

          {/* Visual Failure Timeline */}
          {timelineEvents.length > 0 && <FailureTimeline events={timelineEvents} />}

          <Section title="Maintenance Actions Taken" items={displayRca.maintenance_actions_taken} color="#10b981" />
          <Section title="Lessons Learned" items={displayRca.lessons_learned} color="#6366f1" />
        </div>

        {/* Right column */}
        <div className="space-y-4">
          <Section title="Preventive Recommendations" items={displayRca.preventive_recommendations} color="#3b82f6" />

          {rawResponse?.citations && rawResponse.citations.length > 0 && (
            <div className="glass-card rounded-2xl p-4">
              <p className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-2">
                <FileText className="w-3.5 h-3.5" /> Sources Used
              </p>
              <div className="space-y-2">
                {rawResponse.citations.map((c, i) => (
                  <div key={i} className="px-3 py-2 rounded-lg" style={{ background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.12)" }}>
                    <p className="text-xs font-medium text-blue-300 truncate">{c.document_name}</p>
                    {c.page_number && <p className="text-xs text-slate-600">Page {c.page_number}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Confidence score card (if from live backend) */}
          {rawResponse?.confidence_score != null && (
            <div className="glass-card rounded-2xl p-4">
              <p className="text-xs font-semibold text-slate-400 mb-3">AI Confidence</p>
              <div className="flex items-end gap-2">
                <p className="text-3xl font-bold" style={{ color: "#10b981" }}>
                  {Math.round(rawResponse.confidence_score * 100)}%
                </p>
                <p className="text-xs text-slate-600 mb-1">accuracy</p>
              </div>
              <div className="mt-2 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                <div
                  className="h-full rounded-full transition-all duration-1000"
                  style={{
                    width: `${Math.round(rawResponse.confidence_score * 100)}%`,
                    background: "linear-gradient(90deg, #10b981, #3b82f6)",
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
