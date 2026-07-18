"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  BarChart3, Brain, ChevronLeft, FileText, LayoutDashboard,
  MessageSquare, Network, ShieldCheck, Wrench,
} from "lucide-react";

import AccountMenu from "@/components/AccountMenu";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/documents", icon: FileText, label: "Documents" },
  { href: "/chat", icon: MessageSquare, label: "AI Chat" },
  { href: "/graph", icon: Network, label: "Knowledge Graph" },
  { href: "/maintenance", icon: Wrench, label: "Maintenance" },
  { href: "/compliance", icon: ShieldCheck, label: "Compliance" },
  { href: "/reports", icon: BarChart3, label: "Reports" },
];

interface SidebarProps {
  mobileOpen: boolean;
  onClose: () => void;
  collapsed?: boolean;
  onToggle?: () => void;
}

export default function Sidebar({ mobileOpen, onClose, collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div className="fixed inset-0 z-20 bg-ink/20 md:hidden" onClick={onClose} />
      )}

      <aside
        className={cn(
          "fixed left-0 top-0 z-30 flex h-screen flex-col border-r border-white/5 bg-sidebar",
          "transition-[width,transform] duration-300 md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          collapsed ? "w-16" : "w-60"
        )}
      >
        {/* Collapse handle */}
        {onToggle && (
          <button
            onClick={onToggle}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="absolute -right-3 top-8 z-40 hidden h-6 w-6 items-center justify-center rounded-full border border-line bg-surface text-ink-secondary shadow-e2 transition-colors hover:text-brand md:flex"
          >
            <motion.span animate={{ rotate: collapsed ? 180 : 0 }} transition={{ duration: 0.2 }} className="block">
              <ChevronLeft className="h-3 w-3" />
            </motion.span>
          </button>
        )}

        {/* Brand */}
        <div className={cn("flex items-center gap-2.5 px-4 py-4", collapsed && "justify-center px-0")}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-ui-md bg-brand">
            <Brain className="h-4 w-4 text-white" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-[13px] font-bold leading-tight text-white">IndusMind</p>
              <p className="truncate text-[10px] font-semibold uppercase tracking-wider text-sidebar-ink">
                Knowledge Intelligence
              </p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-2">
          {NAV.map(({ href, icon: Icon, label }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                title={collapsed ? label : undefined}
                className={cn(
                  "group relative flex items-center gap-2.5 rounded-ui-md px-2.5 py-2 text-[13px] font-semibold transition-colors",
                  collapsed && "justify-center px-0",
                  active
                    ? "bg-sidebar-active text-sidebar-ink-active shadow-[0_6px_16px_-6px_rgba(91,94,247,0.7)]"
                    : "text-sidebar-ink hover:bg-sidebar-hover hover:text-white"
                )}
              >
                {/* Icon lifts slightly on hover for a tactile feel. */}
                <motion.span
                  whileHover={{ scale: 1.12 }}
                  transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
                  className="flex shrink-0"
                >
                  <Icon className="h-4 w-4" />
                </motion.span>
                {!collapsed && <span className="truncate">{label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Account — opens a real menu (identity, settings, sign out) rather
            than exposing a bare sign-out icon as the only affordance. */}
        <div className={cn("border-t border-white/5 p-2", collapsed && "px-1")}>
          <AccountMenu collapsed={collapsed} />
        </div>
      </aside>
    </>
  );
}
