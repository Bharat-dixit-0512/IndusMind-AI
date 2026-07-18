"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3, Command, FileText, LayoutDashboard, Menu, MessageSquare,
  Network, Search, ShieldCheck, Sparkles, Wrench,
} from "lucide-react";

import Sidebar from "@/components/Sidebar";
import BackgroundField from "@/components/BackgroundField";
import { useAuth } from "@/context/AuthContext";
import { ChatProvider } from "@/context/ChatContext";
import PageTransitionBar from "@/components/loaders/PageTransitionBar";
import { AuthGuardLoader } from "@/components/loaders/SkeletonLoader";
import { EASE } from "@/components/motion/variants";
import { StatusDot } from "@/components/ui";
import { cn } from "@/lib/utils";

/* The shell deliberately contains no simulated assistant. A previous version
   shipped a floating chat with hardcoded replies ("compliance is currently at
   94%", "Pump P-101 vibration 6.2 mm/s") — fabricated plant data presented as
   AI output. The quick-action now opens the real, document-grounded AI Chat. */

const COMMANDS = [
  { path: "/dashboard", label: "Dashboard", hint: "Executive overview", icon: LayoutDashboard },
  { path: "/documents", label: "Documents", hint: "Upload & processing", icon: FileText },
  { path: "/chat", label: "AI Chat", hint: "Ask your documents", icon: MessageSquare },
  { path: "/graph", label: "Knowledge Graph", hint: "Entities & relationships", icon: Network },
  { path: "/maintenance", label: "Maintenance", hint: "Assets & RCA", icon: Wrench },
  { path: "/compliance", label: "Compliance", hint: "Readiness & findings", icon: ShieldCheck },
  { path: "/reports", label: "Reports", hint: "Generated PDFs", icon: BarChart3 },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [query, setQuery] = useState("");

  // Ctrl/Cmd+K toggles the command palette.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
      if (e.key === "Escape") setPaletteOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!isLoading && !token) router.replace("/");
  }, [isLoading, token, router]);

  if (isLoading) return <AuthGuardLoader />;

  const isChat = pathname === "/chat";
  const results = COMMANDS.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase()) ||
    c.hint.toLowerCase().includes(query.toLowerCase())
  );

  const go = (path: string) => {
    router.push(path);
    setPaletteOpen(false);
    setQuery("");
  };

  return (
    <ChatProvider>
      <PageTransitionBar />
      <BackgroundField />

      {/* Chat owns its own scrolling, so the shell is viewport-bound there. */}
      <div className={cn("relative flex bg-canvas", isChat ? "h-screen overflow-hidden" : "min-h-screen")}>
        <Sidebar
          mobileOpen={mobileMenuOpen}
          onClose={() => setMobileMenuOpen(false)}
          collapsed={collapsed}
          onToggle={() => setCollapsed((c) => !c)}
        />

        <div
          className={cn(
            "flex min-h-0 flex-1 flex-col transition-[margin] duration-300",
            collapsed ? "md:ml-16" : "md:ml-60",
            isChat && "h-screen overflow-hidden"
          )}
        >
          {/* Top bar */}
          <header className="sticky top-0 z-20 flex shrink-0 items-center gap-3 border-b border-line bg-surface/95 px-4 py-2 backdrop-blur">
            <button
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open menu"
              className="rounded-ui-md p-1.5 text-ink-secondary hover:bg-subtle md:hidden"
            >
              <Menu className="h-4 w-4" />
            </button>

            {/* Palette trigger */}
            <button
              onClick={() => setPaletteOpen(true)}
              className="group flex h-8 w-full max-w-sm items-center gap-2 rounded-ui-md border border-line bg-canvas px-2.5 text-left transition-colors hover:border-line-strong"
            >
              <Search className="h-3.5 w-3.5 shrink-0 text-ink-tertiary" />
              <span className="flex-1 truncate text-xs text-ink-tertiary">Jump to…</span>
              <kbd className="hidden items-center gap-0.5 rounded border border-line bg-surface px-1 py-0.5 text-[9px] font-bold text-ink-tertiary sm:inline-flex">
                <Command className="h-2 w-2" />K
              </kbd>
            </button>

            <div className="ml-auto flex items-center gap-3">
              <Link
                href="/chat"
                className="hidden items-center gap-1.5 rounded-ui-md border border-line px-2 py-1 text-[11px] font-semibold text-ink-secondary transition-colors hover:border-brand-line hover:bg-brand-subtle hover:text-brand sm:inline-flex"
              >
                <Sparkles className="h-3 w-3" /> Ask AI
              </Link>
              <span className="hidden items-center gap-1.5 text-[11px] font-semibold text-ink-tertiary sm:inline-flex">
                <StatusDot tone="success" pulse /> Online
              </span>
            </div>
          </header>

          <main className={cn("flex min-h-0 flex-1 flex-col", isChat ? "overflow-hidden" : "pb-10")}>
            {children}
          </main>
        </div>

        {/* Command palette */}
        <AnimatePresence>
          {paletteOpen && (
            <>
              <motion.div
                className="fixed inset-0 z-50 bg-ink/25"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                onClick={() => setPaletteOpen(false)}
              />
              <motion.div
                className="fixed left-1/2 top-24 z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 overflow-hidden rounded-ui-xl border border-line bg-surface shadow-e4"
                initial={{ opacity: 0, y: -8, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.98 }}
                transition={{ duration: 0.18, ease: EASE }}
              >
                <div className="flex items-center gap-2.5 border-b border-line px-4 py-3">
                  <Search className="h-4 w-4 shrink-0 text-ink-tertiary" />
                  <input
                    autoFocus
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && results[0]) go(results[0].path); }}
                    placeholder="Jump to a page…"
                    className="flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-tertiary"
                  />
                </div>
                <div className="max-h-72 overflow-y-auto p-1.5">
                  {results.length === 0 ? (
                    <p className="px-3 py-6 text-center text-xs text-ink-tertiary">No matching pages.</p>
                  ) : (
                    results.map((c) => {
                      const Icon = c.icon;
                      const active = pathname === c.path;
                      return (
                        <button
                          key={c.path}
                          onClick={() => go(c.path)}
                          className={cn(
                            "flex w-full items-center gap-2.5 rounded-ui-md px-2.5 py-2 text-left transition-colors",
                            active ? "bg-brand-subtle" : "hover:bg-subtle"
                          )}
                        >
                          <Icon className={cn("h-4 w-4 shrink-0", active ? "text-brand" : "text-ink-tertiary")} />
                          <span className="min-w-0 flex-1">
                            <span className={cn("block truncate text-xs font-semibold", active ? "text-brand" : "text-ink")}>
                              {c.label}
                            </span>
                            <span className="block truncate text-[11px] text-ink-tertiary">{c.hint}</span>
                          </span>
                        </button>
                      );
                    })
                  )}
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </ChatProvider>
  );
}
