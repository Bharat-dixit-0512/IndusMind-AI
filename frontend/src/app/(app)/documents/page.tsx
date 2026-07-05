"use client";

import { useCallback, useState } from "react";
import { listDocuments, uploadDocument, deleteDocument, type DocumentRecord } from "@/lib/api";
import { useEffect } from "react";
import { Upload, FileText, Trash2, CheckCircle2, Clock, AlertTriangle, RefreshCw, X } from "lucide-react";

function StatusBadge({ status }: { status: DocumentRecord["status"] }) {
  const cfg = {
    COMPLETED:  { icon: CheckCircle2, color: "#10b981", bg: "rgba(16,185,129,0.1)",  label: "Indexed"    },
    PROCESSING: { icon: Clock,        color: "#f59e0b", bg: "rgba(245,158,11,0.1)",  label: "Processing" },
    PENDING:    { icon: Clock,        color: "#6366f1", bg: "rgba(99,102,241,0.1)",  label: "Queued"     },
    FAILED:     { icon: AlertTriangle,color: "#ef4444", bg: "rgba(239,68,68,0.1)",   label: "Failed"     },
  };
  const { icon: Icon, color, bg, label } = cfg[status] ?? cfg.PENDING;
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium" style={{ background: bg, color }}>
      <Icon className="w-3 h-3" />{label}
    </span>
  );
}

const TYPE_COLORS: Record<string, string> = {
  pdf: "#ef4444", xlsx: "#10b981", xls: "#10b981",
  docx: "#3b82f6", doc: "#3b82f6",
  png: "#f59e0b", jpg: "#f59e0b", jpeg: "#f59e0b",
  txt: "#64748b", csv: "#8b5cf6",
};

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState<string[]>([]);
  const [error, setError] = useState("");

  const fetchDocs = useCallback(() => {
    setLoading(true);
    listDocuments().then(setDocs).catch(console.error).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount, not derived render state
    fetchDocs();
  }, [fetchDocs]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setError("");
    const fileArr = Array.from(files);
    for (const file of fileArr) {
      setUploading(u => [...u, file.name]);
      try {
        await uploadDocument(file);
        await fetchDocs();
      } catch (e: unknown) {
        setError(`Failed to upload ${file.name}: ${e instanceof Error ? e.message : "Unknown error"}`);
      } finally {
        setUploading(u => u.filter(n => n !== file.name));
      }
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      setDocs(d => d.filter(doc => doc.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const sampleDocs: DocumentRecord[] = [
    { id: "1", filename: "Manual-Pump-P102.pdf",         file_type: "pdf",  file_size: 2400000, status: "COMPLETED",  uploaded_by: "", created_at: "2026-05-14T09:00:00Z" },
    { id: "2", filename: "SOP-MECH-022.pdf",             file_type: "pdf",  file_size: 800000,  status: "COMPLETED",  uploaded_by: "", created_at: "2026-05-14T09:05:00Z" },
    { id: "3", filename: "WO-9844-RCA.xlsx",             file_type: "xlsx", file_size: 120000,  status: "COMPLETED",  uploaded_by: "", created_at: "2026-05-14T10:00:00Z" },
    { id: "4", filename: "Inspection-C301-Jun2026.pdf",  file_type: "pdf",  file_size: 650000,  status: "PROCESSING", uploaded_by: "", created_at: "2026-06-28T14:00:00Z" },
    { id: "5", filename: "Maintenance-Log-Jun2026.xlsx", file_type: "xlsx", file_size: 200000,  status: "PENDING",    uploaded_by: "", created_at: "2026-07-01T08:30:00Z" },
    { id: "6", filename: "Centurion-Plant-Overview.pdf", file_type: "pdf",  file_size: 5100000, status: "COMPLETED",  uploaded_by: "", created_at: "2026-04-10T11:00:00Z" },
  ];
  const displayDocs = docs.length > 0 ? docs : sampleDocs;

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Document Management</h1>
        <p className="text-sm text-slate-500 mt-1">Upload manuals, SOPs, maintenance records, and inspection reports for AI indexing.</p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: "Total", value: displayDocs.length, color: "#3b82f6" },
          { label: "Indexed", value: displayDocs.filter(d => d.status === "COMPLETED").length, color: "#10b981" },
          { label: "Processing", value: displayDocs.filter(d => d.status === "PROCESSING" || d.status === "PENDING").length, color: "#f59e0b" },
          { label: "Failed", value: displayDocs.filter(d => d.status === "FAILED").length, color: "#ef4444" },
        ].map(s => (
          <div key={s.label} className="glass-card rounded-xl p-4 text-center">
            <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
            <p className="text-xs text-slate-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => document.getElementById("fileInput")?.click()}
        className="relative mb-6 rounded-2xl p-10 text-center cursor-pointer transition-all duration-300"
        style={{
          border: `2px dashed ${dragging ? "#3b82f6" : "rgba(255,255,255,0.08)"}`,
          background: dragging ? "rgba(59,130,246,0.06)" : "rgba(255,255,255,0.02)"
        }}>
        <input id="fileInput" type="file" multiple className="hidden"
          accept=".pdf,.docx,.doc,.xlsx,.xls,.png,.jpg,.jpeg,.txt,.csv"
          onChange={e => handleFiles(e.target.files)} />
        <Upload className="w-10 h-10 mx-auto mb-3 text-blue-500 opacity-60" />
        <p className="text-sm font-medium text-slate-300">Drop files here or <span className="text-blue-400">click to browse</span></p>
        <p className="text-xs text-slate-600 mt-1">Supports PDF, DOCX, XLSX, PNG, JPG, TXT — Max 50MB</p>

        {/* Uploading indicators */}
        {uploading.length > 0 && (
          <div className="mt-4 space-y-2">
            {uploading.map(name => (
              <div key={name} className="flex items-center gap-2 justify-center">
                <div className="w-3 h-3 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
                <span className="text-xs text-blue-400">Uploading {name}…</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl mb-4 text-sm text-red-400"
          style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError("")}><X className="w-4 h-4" /></button>
        </div>
      )}

      {/* Document table */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <h2 className="text-sm font-semibold text-slate-300">Uploaded Files</h2>
          <button onClick={fetchDocs} className="text-slate-500 hover:text-slate-300 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="p-6 space-y-3">
            {[...Array(4)].map((_, i) => <div key={i} className="h-14 rounded-xl animate-pulse" style={{ background: "rgba(255,255,255,0.03)" }} />)}
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: "rgba(255,255,255,0.04)" }}>
            {displayDocs.map(doc => {
              const ext = doc.file_type.toLowerCase();
              const color = TYPE_COLORS[ext] ?? "#64748b";
              return (
                <div key={doc.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-white/[0.02] transition-colors group">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: `${color}18`, border: `1px solid ${color}25` }}>
                    <FileText className="w-4 h-4" style={{ color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-300 truncate">{doc.filename}</p>
                    <p className="text-xs text-slate-600 mt-0.5">
                      {(doc.file_size / 1024).toFixed(0)} KB ·{" "}
                      {ext.toUpperCase()} ·{" "}
                      {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <StatusBadge status={doc.status} />
                  <button onClick={() => handleDelete(doc.id)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-600 hover:text-red-400 ml-2">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
