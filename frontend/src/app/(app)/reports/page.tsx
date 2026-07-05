"use client";

import { useEffect, useState } from "react";
import { listReports, generateReport, getReportDownloadUrl, type ReportRecord } from "@/lib/api";
import { BarChart3, Plus, Download, Loader2, FileText, X } from "lucide-react";

const REPORT_TYPES = [
  { value: "RCA",         label: "Root Cause Analysis",    color: "#ef4444" },
  { value: "COMPLIANCE",  label: "Compliance Audit",       color: "#6366f1" },
  { value: "MAINTENANCE", label: "Maintenance Report",     color: "#10b981" },
  { value: "INSPECTION",  label: "Inspection Summary",     color: "#f59e0b" },
];

const TYPE_COLORS: Record<string, string> = {
  RCA: "#ef4444", COMPLIANCE: "#6366f1", MAINTENANCE: "#10b981", INSPECTION: "#f59e0b",
};

const MOCK_REPORTS: ReportRecord[] = [
  { id: "1", title: "RCA – Pump P-102 Shaft Failure",        report_type: "RCA",         file_path: "/reports/1.pdf", generated_by: "", created_at: "2026-05-14T11:00:00Z" },
  { id: "2", title: "Compliance Audit – SOP-MECH-022",       report_type: "COMPLIANCE",  file_path: "/reports/2.pdf", generated_by: "", created_at: "2026-06-01T09:30:00Z" },
  { id: "3", title: "Monthly Maintenance Summary – May 2026", report_type: "MAINTENANCE", file_path: "/reports/3.pdf", generated_by: "", created_at: "2026-06-01T10:00:00Z" },
  { id: "4", title: "Compressor C-301 Inspection Report",    report_type: "INSPECTION",  file_path: "/reports/4.pdf", generated_by: "", created_at: "2026-06-28T15:00:00Z" },
];

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState("RCA");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    listReports()
      .then(data => setReports(data.length > 0 ? data : MOCK_REPORTS))
      .catch(() => setReports(MOCK_REPORTS))
      .finally(() => setLoading(false));
  }, []);

  const handleGenerate = async () => {
    if (!newTitle.trim()) return;
    setGenerating(true);
    try {
      const report = await generateReport(newTitle, newType);
      setReports(r => [report, ...r]);
    } catch {
      setReports(r => [{
        id: Date.now().toString(),
        title: newTitle,
        report_type: newType,
        file_path: "",
        generated_by: "",
        created_at: new Date().toISOString()
      }, ...r]);
    } finally {
      setGenerating(false);
      setShowModal(false);
      setNewTitle("");
    }
  };

  const counts = REPORT_TYPES.map(t => ({
    ...t,
    count: reports.filter(r => r.report_type === t.value).length,
  }));

  return (
    <div className="p-8">
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)" }}>
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100">Reports</h1>
          </div>
          <p className="text-sm text-slate-500 ml-11">AI-generated PDF reports for RCA, Compliance, Maintenance and Inspection.</p>
        </div>
        <button onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
          style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)", boxShadow: "0 4px 12px rgba(245,158,11,0.3)" }}>
          <Plus className="w-4 h-4" /> Generate Report
        </button>
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {counts.map(c => (
          <div key={c.value} className="glass-card rounded-xl p-4">
            <p className="text-2xl font-bold mb-1" style={{ color: c.color }}>{c.count}</p>
            <p className="text-xs text-slate-500">{c.label}</p>
          </div>
        ))}
      </div>

      {/* Report list */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <h2 className="text-sm font-semibold text-slate-300">Generated Reports</h2>
        </div>
        {loading ? (
          <div className="p-6 space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="h-14 rounded-xl animate-pulse" style={{ background: "rgba(255,255,255,0.03)" }} />)}</div>
        ) : (
          <div className="divide-y" style={{ borderColor: "rgba(255,255,255,0.04)" }}>
            {reports.map(r => {
              const color = TYPE_COLORS[r.report_type] ?? "#64748b";
              return (
                <div key={r.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-white/[0.02] transition-colors">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: `${color}18`, border: `1px solid ${color}25` }}>
                    <FileText className="w-4 h-4" style={{ color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-300 truncate">{r.title}</p>
                    <p className="text-xs text-slate-600 mt-0.5">
                      {r.report_type} · {new Date(r.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </p>
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-xs font-medium flex-shrink-0" style={{ background: `${color}15`, color }}>
                    {r.report_type}
                  </span>
                  {r.id && (
                    <a href={getReportDownloadUrl(r.id)} target="_blank" rel="noopener noreferrer"
                      className="text-slate-600 hover:text-blue-400 transition-colors p-1 ml-1">
                      <Download className="w-4 h-4" />
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Generate modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}>
          <div className="glass-panel rounded-2xl p-6 w-full max-w-md" style={{ boxShadow: "0 25px 50px rgba(0,0,0,0.6)" }}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-slate-100">Generate New Report</h2>
              <button onClick={() => setShowModal(false)} className="text-slate-500 hover:text-slate-300 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Report Title</label>
                <input value={newTitle} onChange={e => setNewTitle(e.target.value)}
                  placeholder="e.g. RCA – Pump P-102 Seal Failure"
                  className="w-full px-4 py-2.5 rounded-xl text-sm text-slate-200 placeholder:text-slate-600 outline-none"
                  style={{ background: "rgba(15,23,42,0.7)", border: "1px solid rgba(255,255,255,0.08)" }} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Report Type</label>
                <div className="grid grid-cols-2 gap-2">
                  {REPORT_TYPES.map(t => (
                    <button key={t.value} onClick={() => setNewType(t.value)}
                      className="px-3 py-2.5 rounded-xl text-xs font-medium transition-all"
                      style={newType === t.value
                        ? { background: `${t.color}20`, border: `1.5px solid ${t.color}50`, color: t.color }
                        : { background: "rgba(255,255,255,0.03)", border: "1.5px solid rgba(255,255,255,0.07)", color: "#64748b" }}>
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
              <button onClick={handleGenerate} disabled={!newTitle.trim() || generating}
                className="w-full py-3 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-50"
                style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)", boxShadow: "0 4px 12px rgba(245,158,11,0.25)" }}>
                {generating ? <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />Generating…</span> : "Generate PDF Report →"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
