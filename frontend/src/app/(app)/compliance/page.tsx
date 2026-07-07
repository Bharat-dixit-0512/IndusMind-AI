"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchComplianceOverview, generateReport, getReportDownloadUrl,
  type ComplianceOverview,
} from "@/lib/api";
import {
  ShieldCheck, Loader2, CheckCircle2, XCircle, Download, AlertTriangle,
  ShieldAlert, FileWarning, RefreshCw, FileText,
} from "lucide-react";

const RISK_COLORS: Record<string, string> = {
  Low: "#10b981", Medium: "#f59e0b", High: "#f97316", Critical: "#ef4444", Unknown: "#64748b",
};

export default function CompliancePage() {
  const [overview, setOverview] = useState<ComplianceOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    fetchComplianceOverview()
      .then(setOverview)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount, not derived render state
    load();
  }, [load]);

  const downloadReport = async () => {
    setGenerating(true);
    try {
      const r = await generateReport("Compliance Audit", "COMPLIANCE");
      window.open(getReportDownloadUrl(r.id), "_blank");
    } catch (e) { console.error(e); }
    finally { setGenerating(false); }
  };

  const score = overview?.compliance_score ?? 0;
  const scoreColor = !overview?.has_data ? "#64748b" : score >= 90 ? "#10b981" : score >= 70 ? "#f59e0b" : "#ef4444";
  const riskColor = RISK_COLORS[overview?.risk_level ?? "Unknown"];

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-start justify-between mb-6 gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "linear-gradient(135deg, #6366f1, #4f46e5)" }}>
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">Compliance Auditor</h1>
          </div>
          <p className="text-sm text-slate-500 ml-11">Compliance status inferred automatically from your uploaded SOPs, inspection, audit and safety documents.</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-slate-300 flex-shrink-0 transition-all" style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="glass-card rounded-2xl p-10 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
        </div>
      ) : !overview?.has_data ? (
        <div className="glass-card rounded-2xl p-10 text-center">
          <FileWarning className="w-8 h-8 mx-auto mb-3 text-slate-700" />
          <p className="text-sm text-slate-400">No compliance data yet</p>
          <p className="text-xs text-slate-600 mt-1 max-w-md mx-auto">{overview?.message}</p>
          {overview && overview.missing_documents.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2 justify-center">
              {overview.missing_documents.map(m => (
                <span key={m} className="px-2.5 py-1 rounded-full text-xs text-slate-500" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>{m}</span>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          {/* Left: main results */}
          <div className="xl:col-span-2 space-y-4">
            {/* Score + risk card */}
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-6 flex-wrap">
                <div className="relative flex-shrink-0">
                  <svg width="90" height="90" viewBox="0 0 90 90">
                    <circle cx="45" cy="45" r="38" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
                    <circle cx="45" cy="45" r="38" fill="none" stroke={scoreColor} strokeWidth="8"
                      strokeDasharray={`${score * 2.389} 238.9`} strokeLinecap="round" transform="rotate(-90 45 45)" />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-xl font-bold" style={{ color: scoreColor }}>{score}%</span>
                  </div>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-lg font-bold text-slate-100">Compliance Score</h2>
                    <span className="px-2 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1" style={{ background: `${riskColor}18`, color: riskColor, border: `1px solid ${riskColor}40` }}>
                      <ShieldAlert className="w-3 h-3" /> {overview.risk_level} Risk
                    </span>
                  </div>
                  <p className="text-sm text-slate-400 mb-3">{overview.summary}</p>
                  <div className="flex gap-4 flex-wrap">
                    <span className="flex items-center gap-1.5 text-xs text-emerald-400"><CheckCircle2 className="w-3.5 h-3.5" />{overview.passed_checks} Passed</span>
                    <span className="flex items-center gap-1.5 text-xs text-red-400"><XCircle className="w-3.5 h-3.5" />{overview.failed_checks} Failed</span>
                  </div>
                </div>
                <button onClick={downloadReport} disabled={generating}
                  className="ml-auto flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-slate-300 flex-shrink-0 transition-all"
                  style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
                  {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                  Export PDF
                </button>
              </div>
            </div>

            {/* Deviations / checklist */}
            {overview.checklist.length > 0 && (
              <div className="glass-card rounded-2xl overflow-hidden">
                <div className="px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <h2 className="text-sm font-semibold text-slate-300">Parameter Checklist & Deviations</h2>
                </div>
                <div className="divide-y" style={{ borderColor: "rgba(255,255,255,0.04)" }}>
                  {overview.checklist.map((item, i) => (
                    <div key={i} className="flex items-center gap-4 px-5 py-3.5">
                      {item.status === "COMPLIANT" ? <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" /> : <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-300">{item.parameter}</p>
                        {item.deviation && item.deviation !== "None" && <p className="text-xs text-red-400 mt-0.5">{item.deviation}</p>}
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-xs text-slate-500">SOP: <span className="text-slate-400">{item.sop_limit}</span></p>
                        <p className="text-xs" style={{ color: item.status === "COMPLIANT" ? "#10b981" : "#ef4444" }}>Actual: {item.inspected_value}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {overview.checklist.length === 0 && (
              <div className="glass-card rounded-2xl p-6 text-center">
                <p className="text-sm text-slate-400">{overview.summary || "No specific parameter deviations were extracted from the uploaded documents."}</p>
                <p className="text-xs text-slate-600 mt-1">The assessment is based on the detected compliance documents listed on the right.</p>
              </div>
            )}
          </div>

          {/* Right column */}
          <div className="space-y-4">
            {overview.corrective_actions.length > 0 && (
              <div className="glass-card rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-4"><AlertTriangle className="w-4 h-4 text-amber-400" /><h2 className="text-sm font-semibold text-slate-300">Corrective Actions</h2></div>
                <div className="space-y-3">
                  {overview.corrective_actions.map((action, i) => (
                    <div key={i} className="flex gap-3 p-3 rounded-xl" style={{ background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.12)" }}>
                      <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-amber-400 flex-shrink-0 mt-0.5" style={{ background: "rgba(245,158,11,0.15)" }}>{i + 1}</span>
                      <p className="text-xs text-slate-400 leading-relaxed">{action}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Detected documents */}
            <div className="glass-card rounded-2xl p-4">
              <p className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-2"><FileText className="w-3.5 h-3.5" /> Detected Compliance Documents</p>
              <div className="space-y-2">
                {overview.detected_documents.map(d => (
                  <div key={d.id} className="px-3 py-2 rounded-lg" style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.12)" }}>
                    <p className="text-xs font-medium text-slate-300 truncate">{d.filename}</p>
                    <p className="text-[10px] text-indigo-300 mt-0.5">{d.category}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Missing document types */}
            {overview.missing_documents.length > 0 && (
              <div className="glass-card rounded-2xl p-4">
                <p className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-2"><FileWarning className="w-3.5 h-3.5 text-amber-400" /> Missing Document Types</p>
                <div className="flex flex-wrap gap-2">
                  {overview.missing_documents.map(m => (
                    <span key={m} className="px-2.5 py-1 rounded-full text-xs text-amber-300" style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.18)" }}>{m}</span>
                  ))}
                </div>
                <p className="text-[10px] text-slate-600 mt-2">Uploading these would strengthen the compliance assessment.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
