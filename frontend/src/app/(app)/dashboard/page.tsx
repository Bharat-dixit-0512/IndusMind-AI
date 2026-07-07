"use client";

import { useEffect, useState, useCallback } from "react";
import { listDocuments, type DocumentRecord } from "@/lib/api";
import {
  FileText, AlertTriangle, CheckCircle2, Clock, Upload, QrCode
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";

interface StatCard { label: string; value: string | number; icon: React.ElementType; color: string; sub?: string; trend?: string; trendUp?: boolean; }

function StatTile({ label, value, icon: Icon, color, sub, trend, trendUp }: StatCard) {
  return (
    <div className="glass-card rounded-2xl p-5 transition-all duration-300 glass-card-hover relative overflow-hidden group">
      {/* Background radial glow */}
      <div className="absolute -right-8 -bottom-8 w-24 h-24 rounded-full opacity-0 group-hover:opacity-10 transition-opacity duration-500 blur-xl"
        style={{ background: color }} />
      
      <div className="flex items-start justify-between mb-4 relative z-10">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: `${color}20`, border: `1px solid ${color}30` }}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        {trend && (
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
            trendUp ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"
          }`}>
            {trend}
          </span>
        )}
      </div>
      <p className="text-3xl font-bold text-slate-100 mb-1 tracking-tight relative z-10">{value}</p>
      <p className="text-xs text-slate-400 font-medium relative z-10">{label}</p>
      {sub && <p className="text-xs text-slate-500 mt-1.5 font-mono relative z-10">{sub}</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: DocumentRecord["status"] }) {
  const cfg = {
    COMPLETED:  { icon: CheckCircle2, color: "#10b981", bg: "rgba(16,185,129,0.1)",  label: "Indexed"    },
    PROCESSING: { icon: Clock,        color: "#f59e0b", bg: "rgba(245,158,11,0.1)",  label: "Processing" },
    PENDING:    { icon: Clock,        color: "#6366f1", bg: "rgba(99,102,241,0.1)",  label: "Pending"    },
    FAILED:     { icon: AlertTriangle,color: "#ef4444", bg: "rgba(239,68,68,0.1)",   label: "Failed"     },
  };
  const { icon: Icon, color, bg, label } = cfg[status] ?? cfg.PENDING;
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
      style={{ background: bg, color }}>
      <Icon className="w-3 h-3" />{label}
    </span>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showQrSim, setShowQrSim] = useState(false);
  const [qrScanning, setQrScanning] = useState(false);

  const fetchDocs = useCallback(async () => {
    try {
      const data = await listDocuments();
      setDocs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount, not derived render state
    fetchDocs();
  }, [fetchDocs]);

  const completed = docs.filter(d => d.status === "COMPLETED").length;
  const processing = docs.filter(d => d.status === "PROCESSING" || d.status === "PENDING").length;
  const failed = docs.filter(d => d.status === "FAILED").length;
  const indexedPct = docs.length ? Math.round((completed / docs.length) * 100) : 0;

  const stats: StatCard[] = [
    { label: "Documents Uploaded", value: docs.length, icon: FileText, color: "#3b82f6" },
    { label: "Indexed & Searchable", value: completed, icon: CheckCircle2, color: "#10b981", sub: docs.length ? `${indexedPct}% of uploads` : undefined },
    { label: "Processing", value: processing, icon: Clock, color: "#f59e0b" },
    { label: "Failed", value: failed, icon: AlertTriangle, color: "#ef4444" },
  ];

  const recentDocs: DocumentRecord[] = docs.slice(0, 5);

  const suggestedQueries = [
    "What documents have I uploaded?",
    "Summarize my most recent upload",
    "What are the key details in my documents?",
  ];

  const handleSimulateQr = () => {
    setQrScanning(true);
    setTimeout(() => {
      setQrScanning(false);
      setShowQrSim(false);
      // Redirect directly to chat pre-filled with the scanned asset question
      router.push(`/chat?q=${encodeURIComponent("What documents do I have for this asset?")}`);
    }, 2200);
  };

  return (
    <div className="p-4 md:p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400 font-medium">Document Intelligence Platform — Active</span>
          </div>
          <h1 className="text-3xl font-bold text-slate-100">
            Good {new Date().getHours() < 12 ? "morning" : "afternoon"},{" "}
            <span style={{ background: "linear-gradient(90deg, #3b82f6, #10b981)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              {user?.name?.split(" ")[0] ?? "Engineer"}
            </span>
          </h1>
          <p className="text-slate-500 text-sm mt-1">Unified operations intelligence console and multi-agent hub.</p>
        </div>
        
        {/* QR Simulation Button */}
        <button onClick={() => setShowQrSim(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all duration-200"
          style={{ background: "linear-gradient(135deg, #8b5cf6, #6d28d9)", boxShadow: "0 4px 15px rgba(139,92,246,0.3)" }}>
          <QrCode className="w-4 h-4" /> Asset QR Scan
        </button>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {stats.map(s => <StatTile key={s.label} {...s} />)}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        {/* Recent uploads */}
        <div className="glass-card rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-300">Operations Feed</h2>
            <Link href="/documents" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">View all documents →</Link>
          </div>
          {loading ? (
            <div className="space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="h-12 rounded-lg animate-pulse" style={{ background: "rgba(255,255,255,0.03)" }} />)}</div>
          ) : recentDocs.length === 0 ? (
            <p className="text-xs text-slate-600 py-4 text-center">No documents uploaded yet.</p>
          ) : (
            <div className="space-y-2">
              {recentDocs.map(doc => (
                <div key={doc.id} className="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors"
                  style={{ background: "rgba(255,255,255,0.02)" }}>
                  <FileText className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-300 truncate">{doc.filename}</p>
                    <p className="text-xs text-slate-600">{(doc.file_size / 1024).toFixed(0)} KB • {doc.file_type.toUpperCase()}</p>
                  </div>
                  <StatusBadge status={doc.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick queries */}
        <div className="glass-card rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-300">Quick AI Query Shortcuts</h2>
            <Link href="/chat" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">Open Chat →</Link>
          </div>
          <div className="grid grid-cols-1 gap-2">
            {suggestedQueries.map(q => (
              <Link key={q} href={`/chat?q=${encodeURIComponent(q)}`}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs text-slate-400 hover:text-slate-200 transition-all duration-200 group"
                style={{ background: "rgba(255,255,255,0.02)", border: "1px solid transparent" }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = "rgba(59,130,246,0.2)")}
                onMouseLeave={e => (e.currentTarget.style.borderColor = "transparent")}>
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500/50 flex-shrink-0 group-hover:bg-blue-400 transition-colors" />
                {q}
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Upload CTA */}
      <Link href="/documents"
        className="flex items-center gap-4 p-5 rounded-2xl transition-all duration-300 group"
        style={{ background: "linear-gradient(135deg, rgba(59,130,246,0.08), rgba(16,185,129,0.08))", border: "1px solid rgba(59,130,246,0.15)" }}
        onMouseEnter={e => (e.currentTarget.style.borderColor = "rgba(59,130,246,0.35)")}
        onMouseLeave={e => (e.currentTarget.style.borderColor = "rgba(59,130,246,0.15)")}>
        <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: "rgba(59,130,246,0.15)", border: "1px solid rgba(59,130,246,0.25)" }}>
          <Upload className="w-6 h-6 text-blue-400" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-200">Upload New Documents</p>
          <p className="text-xs text-slate-500 mt-0.5">Add PDFs, SOPs, maintenance records, inspection reports or Excel logs</p>
        </div>
        <span className="text-blue-400 group-hover:translate-x-1 transition-transform">→</span>
      </Link>

      {/* QR Code Scan Simulator Modal */}
      {showQrSim && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.8)", backdropFilter: "blur(6px)" }}>
          <div className="glass-panel rounded-2xl p-6 w-full max-w-md text-center" style={{ boxShadow: "0 25px 50px rgba(0,0,0,0.6)" }}>
            <h2 className="text-lg font-bold text-slate-100 mb-2">Simulated Asset QR Scanner</h2>
            <p className="text-xs text-slate-500 mb-6">Scan QR tag on plant assets to retrieve documentation & maintenance guides.</p>

            {/* Scan animation container */}
            <div className="w-56 h-56 mx-auto mb-6 relative rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center"
              style={{ background: "rgba(5,7,15,0.7)" }}>
              {qrScanning ? (
                <>
                  <div className="absolute top-0 left-0 w-full h-1 bg-violet-500 shadow-[0_0_15px_#8b5cf6] animate-bounce" style={{ animationDuration: "2s" }} />
                  <QrCode className="w-24 h-24 text-violet-500 opacity-60 animate-pulse" />
                </>
              ) : (
                <div className="text-center p-4">
                  <QrCode className="w-16 h-16 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs text-slate-400">Position scanner over an asset tag</p>
                </div>
              )}
            </div>

            <div className="flex gap-3 justify-center">
              <button onClick={() => setShowQrSim(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 transition-colors"
                style={{ background: "rgba(255,255,255,0.05)" }}>
                Cancel
              </button>
              <button onClick={handleSimulateQr} disabled={qrScanning}
                className="px-5 py-2.5 rounded-xl text-xs font-semibold text-white transition-all"
                style={{ background: "linear-gradient(135deg, #8b5cf6, #6d28d9)" }}>
                {qrScanning ? "Scanning Tag…" : "Scan Asset Tag"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
