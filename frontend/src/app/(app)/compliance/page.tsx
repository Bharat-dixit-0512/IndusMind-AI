"use client";

import { useState } from "react";
import { runComplianceCheck, generateReport, getReportDownloadUrl } from "@/lib/api";
import { ShieldCheck, Loader2, CheckCircle2, XCircle, Download, AlertTriangle } from "lucide-react";

interface ChecklistItem {
  parameter: string;
  sop_limit: string;
  inspected_value: string;
  status: "COMPLIANT" | "NON_COMPLIANT";
  deviation: string;
}

interface ComplianceReport {
  compliance_score: number;
  summary: string;
  checklist: ChecklistItem[];
  corrective_actions: string[];
}

const MOCK_REPORT: ComplianceReport = {
  compliance_score: 75,
  summary: "The shaft alignment inspection for Centrifugal Pump P-102 failed to meet tolerances defined in SOP-MECH-022. Vibration amplitude and seal leak rate are critically non-compliant. Corrective action required before returning to service.",
  checklist: [
    { parameter: "Radial Shaft Misalignment", sop_limit: "Max 0.05 mm", inspected_value: "0.08 mm", status: "NON_COMPLIANT", deviation: "Exceeds tolerance by 0.03 mm" },
    { parameter: "Vibration Amplitude (RMS)", sop_limit: "Max 2.8 mm/s", inspected_value: "4.2 mm/s", status: "NON_COMPLIANT", deviation: "Exceeds alert limit by 1.4 mm/s" },
    { parameter: "Casing Temperature",         sop_limit: "Max 75°C",     inspected_value: "72°C",    status: "COMPLIANT",     deviation: "None" },
    { parameter: "Mechanical Seal Leak Rate",  sop_limit: "Max 3 drops/min", inspected_value: "12 drops/min", status: "NON_COMPLIANT", deviation: "Excessive leakage — seal face wear suspected" },
    { parameter: "Bearing Housing Temp",       sop_limit: "Max 85°C",     inspected_value: "78°C",    status: "COMPLIANT",     deviation: "None" },
    { parameter: "Lubrication Oil Level",      sop_limit: "Min sight glass midline", inspected_value: "At midline", status: "COMPLIANT", deviation: "None" },
  ],
  corrective_actions: [
    "Shutdown Pump P-102 immediately to prevent catastrophic bearing failure.",
    "Perform laser shaft realignment per SOP-MECH-022 Section 3.",
    "Replace mechanical seal with Spare Part: Seal S-100.",
    "Re-run vibration baseline sweep before returning to service.",
  ],
};

export default function CompliancePage() {
  const [query, setQuery] = useState("Pump P-102 shaft alignment inspection");
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ComplianceReport>(MOCK_REPORT);
  const [generating, setGenerating] = useState(false);

  const runCheck = async () => {
    setLoading(true);
    try {
      const result = await runComplianceCheck(query) as ComplianceReport;
      if (result.compliance_score !== undefined) setReport(result);
    } catch { /* keep mock */ }
    finally { setLoading(false); }
  };

  const downloadReport = async () => {
    setGenerating(true);
    try {
      const r = await generateReport(`Compliance Audit – ${query}`, "COMPLIANCE");
      window.open(getReportDownloadUrl(r.id), "_blank");
    } catch (e) { console.error(e); }
    finally { setGenerating(false); }
  };

  const scoreColor = report.compliance_score >= 90 ? "#10b981" : report.compliance_score >= 70 ? "#f59e0b" : "#ef4444";
  const compliant = report.checklist.filter(c => c.status === "COMPLIANT").length;
  const nonCompliant = report.checklist.filter(c => c.status === "NON_COMPLIANT").length;

  return (
    <div className="p-8">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "linear-gradient(135deg, #6366f1, #4f46e5)" }}>
            <ShieldCheck className="w-4 h-4 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Compliance Auditor</h1>
        </div>
        <p className="text-sm text-slate-500 ml-11">Automatically checks inspection reports against SOPs and generates compliance scores.</p>
      </div>

      {/* Query bar */}
      <div className="glass-card rounded-2xl p-5 mb-6">
        <div className="flex gap-3">
          <input value={query} onChange={e => setQuery(e.target.value)}
            placeholder="Enter asset or inspection to audit…"
            className="flex-1 px-4 py-2.5 rounded-xl text-sm text-slate-200 placeholder:text-slate-600 outline-none"
            style={{ background: "rgba(15,23,42,0.7)", border: "1px solid rgba(255,255,255,0.08)" }} />
          <button onClick={runCheck} disabled={loading}
            className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-50"
            style={{ background: "linear-gradient(135deg, #6366f1, #4f46e5)", boxShadow: "0 4px 12px rgba(99,102,241,0.3)" }}>
            {loading ? <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />Auditing…</span> : "Run Audit →"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Left: main results */}
        <div className="xl:col-span-2 space-y-4">
          {/* Score card */}
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center gap-6">
              {/* Donut score */}
              <div className="relative flex-shrink-0">
                <svg width="90" height="90" viewBox="0 0 90 90">
                  <circle cx="45" cy="45" r="38" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
                  <circle cx="45" cy="45" r="38" fill="none" stroke={scoreColor} strokeWidth="8"
                    strokeDasharray={`${report.compliance_score * 2.389} 238.9`}
                    strokeLinecap="round" transform="rotate(-90 45 45)" />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xl font-bold" style={{ color: scoreColor }}>{report.compliance_score}%</span>
                </div>
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-100 mb-1">Compliance Score</h2>
                <p className="text-sm text-slate-400 mb-3">{report.summary}</p>
                <div className="flex gap-4">
                  <span className="flex items-center gap-1.5 text-xs text-emerald-400"><CheckCircle2 className="w-3.5 h-3.5" />{compliant} Compliant</span>
                  <span className="flex items-center gap-1.5 text-xs text-red-400"><XCircle className="w-3.5 h-3.5" />{nonCompliant} Non-Compliant</span>
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

          {/* Checklist */}
          <div className="glass-card rounded-2xl overflow-hidden">
            <div className="px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
              <h2 className="text-sm font-semibold text-slate-300">Parameter Checklist</h2>
            </div>
            <div className="divide-y" style={{ borderColor: "rgba(255,255,255,0.04)" }}>
              {report.checklist.map((item, i) => (
                <div key={i} className="flex items-center gap-4 px-5 py-3.5">
                  {item.status === "COMPLIANT"
                    ? <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    : <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-300">{item.parameter}</p>
                    {item.deviation !== "None" && <p className="text-xs text-red-400 mt-0.5">{item.deviation}</p>}
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-slate-500">SOP: <span className="text-slate-400">{item.sop_limit}</span></p>
                    <p className="text-xs" style={{ color: item.status === "COMPLIANT" ? "#10b981" : "#ef4444" }}>
                      Actual: {item.inspected_value}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: corrective actions */}
        <div>
          <div className="glass-card rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-semibold text-slate-300">Corrective Actions Required</h2>
            </div>
            <div className="space-y-3">
              {report.corrective_actions.map((action, i) => (
                <div key={i} className="flex gap-3 p-3 rounded-xl" style={{ background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.12)" }}>
                  <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-amber-400 flex-shrink-0 mt-0.5"
                    style={{ background: "rgba(245,158,11,0.15)" }}>{i + 1}</span>
                  <p className="text-xs text-slate-400 leading-relaxed">{action}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
