"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Eye, EyeOff, Zap, Shield, Brain, Activity } from "lucide-react";

export default function HomePage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "ENGINEER" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPwd, setShowPwd] = useState(false);

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login({ email: form.email, password: form.password });
      } else {
        await register({ email: form.email, password: form.password, full_name: form.full_name, role: form.role });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: Brain, label: "AI Knowledge RAG", desc: "Ask any engineering question with full document citations" },
    { icon: Activity, label: "Failure Intelligence", desc: "Root Cause Analysis generated from maintenance history" },
    { icon: Shield, label: "Compliance Auditing", desc: "Auto-check inspection reports against SOPs" },
    { icon: Zap, label: "Knowledge Graph", desc: "Interactive React Flow graph of assets, engineers & failures" },
  ];

  return (
    <div className="min-h-screen flex" style={{ background: "radial-gradient(ellipse at 10% 20%, rgba(15,23,42,1) 0%, rgba(5,7,15,1) 60%, rgba(15,23,42,1) 100%)" }}>
      {/* Left panel - branding */}
      <div className="hidden lg:flex flex-1 flex-col justify-center px-16 py-12 relative overflow-hidden">
        {/* Ambient glow */}
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full opacity-20 blur-3xl" style={{ background: "radial-gradient(circle, #3b82f6, transparent)" }} />
        <div className="absolute bottom-0 right-0 w-80 h-80 rounded-full opacity-15 blur-3xl" style={{ background: "radial-gradient(circle, #10b981, transparent)" }} />

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #3b82f6, #1d4ed8)" }}>
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <p className="text-xs text-blue-400 font-semibold tracking-widest uppercase">ET AI Hackathon 2026</p>
            </div>
          </div>

          <h1 className="text-5xl font-bold leading-tight mb-4" style={{ color: "#f8fafc" }}>
            Industrial<br />
            <span style={{ background: "linear-gradient(90deg, #3b82f6, #10b981)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              AI Brain
            </span>
          </h1>
          <p className="text-lg text-slate-400 mb-12 max-w-md">
            Unified <span className="text-blue-400 font-medium">Document Intelligence</span> for your organization.
            Upload documents, visualize knowledge, and query with citations.
          </p>

          <div className="space-y-4">
            {features.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex items-start gap-4 glass-card rounded-xl p-4 transition-all duration-300 glass-card-hover cursor-default">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: "rgba(59,130,246,0.15)", border: "1px solid rgba(59,130,246,0.25)" }}>
                  <Icon className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-200">{label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel - auth form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12 lg:px-12">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #3b82f6, #1d4ed8)" }}>
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-slate-100">Industrial AI Brain</span>
          </div>

          <div className="glass-panel rounded-2xl p-8" style={{ boxShadow: "0 25px 50px rgba(0,0,0,0.5)" }}>
            <h2 className="text-2xl font-bold text-slate-100 mb-1">
              {mode === "login" ? "Welcome back" : "Create account"}
            </h2>
            <p className="text-sm text-slate-500 mb-8">
              {mode === "login" ? "Sign in to your operations dashboard" : "Register to access the AI platform"}
            </p>

            {/* Mode tabs */}
            <div className="flex rounded-lg p-1 mb-6" style={{ background: "rgba(15,23,42,0.6)" }}>
              {(["login", "register"] as const).map(m => (
                <button key={m} onClick={() => { setMode(m); setError(""); }}
                  className="flex-1 py-2 rounded-md text-sm font-medium transition-all duration-200"
                  style={mode === m ? { background: "linear-gradient(135deg, #3b82f6, #1d4ed8)", color: "#fff" } : { color: "#64748b" }}>
                  {m === "login" ? "Sign In" : "Register"}
                </button>
              ))}
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "register" && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Full Name</label>
                  <input value={form.full_name} onChange={e => set("full_name", e.target.value)} required
                    placeholder="Elena Rostova"
                    className="w-full px-4 py-2.5 rounded-lg text-sm text-slate-200 outline-none transition-all"
                    style={{ background: "rgba(15,23,42,0.7)", border: "1px solid rgba(255,255,255,0.07)" }}
                    onFocus={e => (e.target.style.borderColor = "rgba(59,130,246,0.5)")}
                    onBlur={e => (e.target.style.borderColor = "rgba(255,255,255,0.07)")} />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Email Address</label>
                <input type="email" value={form.email} onChange={e => set("email", e.target.value)} required
                  placeholder="you@company.com"
                  className="w-full px-4 py-2.5 rounded-lg text-sm text-slate-200 outline-none transition-all"
                  style={{ background: "rgba(15,23,42,0.7)", border: "1px solid rgba(255,255,255,0.07)" }}
                  onFocus={e => (e.target.style.borderColor = "rgba(59,130,246,0.5)")}
                  onBlur={e => (e.target.style.borderColor = "rgba(255,255,255,0.07)")} />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Password</label>
                <div className="relative">
                  <input type={showPwd ? "text" : "password"} value={form.password} onChange={e => set("password", e.target.value)} required
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 pr-11 rounded-lg text-sm text-slate-200 outline-none transition-all"
                    style={{ background: "rgba(15,23,42,0.7)", border: "1px solid rgba(255,255,255,0.07)" }}
                    onFocus={e => (e.target.style.borderColor = "rgba(59,130,246,0.5)")}
                    onBlur={e => (e.target.style.borderColor = "rgba(255,255,255,0.07)")} />
                  <button type="button" onClick={() => setShowPwd(s => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                    {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {mode === "register" && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Role</label>
                  <select value={form.role} onChange={e => set("role", e.target.value)}
                    className="w-full px-4 py-2.5 rounded-lg text-sm text-slate-200 outline-none"
                    style={{ background: "rgba(15,23,42,0.7)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <option value="ENGINEER">Engineer</option>
                    <option value="INSPECTOR">Inspector</option>
                    <option value="ADMIN">Administrator</option>
                  </select>
                </div>
              )}

              {error && (
                <div className="px-4 py-3 rounded-lg text-sm text-red-400" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
                  {error}
                </div>
              )}

              <button type="submit" disabled={loading}
                className="w-full py-3 rounded-lg text-sm font-semibold text-white transition-all duration-200 mt-2 disabled:opacity-60"
                style={{ background: loading ? "rgba(59,130,246,0.5)" : "linear-gradient(135deg, #3b82f6, #1d4ed8)", boxShadow: "0 4px 15px rgba(59,130,246,0.3)" }}>
                {loading ? "Authenticating…" : mode === "login" ? "Sign In →" : "Create Account →"}
              </button>
            </form>

            {mode === "login" && (
              <p className="mt-6 text-center text-xs text-slate-600">
                Demo: <span className="text-blue-400">admin@industrial.ai</span> / <span className="text-blue-400">adminpassword123</span>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
