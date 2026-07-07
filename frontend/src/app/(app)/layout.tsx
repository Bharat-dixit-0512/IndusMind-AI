"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Menu, Brain } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { ChatProvider } from "@/context/ChatContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuth();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !token) router.replace("/");
  }, [isLoading, token, router]);

  if (isLoading || !token) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <ChatProvider>
      <div className="flex min-h-screen">
        <Sidebar mobileOpen={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
        <div className="flex-1 md:ml-64 overflow-x-hidden">
          {/* Mobile-only top bar: hamburger + brand, since the sidebar is an
              off-canvas drawer (not part of layout flow) below the md breakpoint */}
          <div className="md:hidden flex items-center gap-3 px-4 py-3 sticky top-0 z-10"
            style={{ background: "rgba(5,7,15,0.95)", borderBottom: "1px solid rgba(255,255,255,0.05)", backdropFilter: "blur(20px)" }}>
            <button onClick={() => setMobileMenuOpen(true)} className="text-slate-300 p-1" aria-label="Open menu">
              <Menu className="w-5 h-5" />
            </button>
            <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ background: "linear-gradient(135deg, #3b82f6, #1d4ed8)" }}>
              <Brain className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold text-slate-100">Industrial AI Brain</span>
          </div>
          <main>{children}</main>
        </div>
      </div>
    </ChatProvider>
  );
}
