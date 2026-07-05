"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, FileText, MessageSquare, Network,
  Wrench, ShieldCheck, BarChart3, LogOut, Brain, ChevronRight
} from "lucide-react";

const NAV = [
  { href: "/dashboard",   icon: LayoutDashboard, label: "Dashboard"    },
  { href: "/documents",   icon: FileText,         label: "Documents"    },
  { href: "/chat",        icon: MessageSquare,    label: "AI Chat"      },
  { href: "/graph",       icon: Network,          label: "Knowledge Graph" },
  { href: "/maintenance", icon: Wrench,           label: "Maintenance"  },
  { href: "/compliance",  icon: ShieldCheck,      label: "Compliance"   },
  { href: "/reports",     icon: BarChart3,        label: "Reports"      },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 flex flex-col z-30"
      style={{ background: "rgba(5,7,15,0.95)", borderRight: "1px solid rgba(255,255,255,0.05)", backdropFilter: "blur(20px)" }}>

      {/* Logo */}
      <div className="px-5 py-6 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: "linear-gradient(135deg, #3b82f6, #1d4ed8)", boxShadow: "0 4px 12px rgba(59,130,246,0.35)" }}>
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-100 leading-tight">Industrial AI</p>
          <p className="text-xs text-blue-400 leading-tight">Brain</p>
        </div>
      </div>

      <div className="mx-4 mb-4 h-px" style={{ background: "rgba(255,255,255,0.05)" }} />

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link key={href} href={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group"
              style={active
                ? { background: "rgba(59,130,246,0.15)", color: "#60a5fa", borderLeft: "2px solid #3b82f6" }
                : { color: "#64748b", borderLeft: "2px solid transparent" }}>
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight className="w-3 h-3 opacity-60" />}
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="p-4">
        <div className="glass-card rounded-xl p-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #6366f1, #4f46e5)" }}>
            {user?.name?.charAt(0) ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-slate-300 truncate">{user?.name ?? "User"}</p>
            <p className="text-xs text-slate-600 truncate">{user?.role}</p>
          </div>
          <button onClick={logout} title="Sign out"
            className="text-slate-600 hover:text-red-400 transition-colors p-1">
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
