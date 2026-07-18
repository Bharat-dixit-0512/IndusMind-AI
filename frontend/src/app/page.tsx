"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { animate, motion, useReducedMotion } from "framer-motion";
import {
  AlertTriangle, Brain, Eye, EyeOff, FileCheck2, FileText, Lock, Mail,
  Network, ShieldCheck, Sparkles, User, Wrench,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { EASE } from "@/components/motion/variants";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────────────────────────
   Every figure on this page is a verifiable property of the product, not a
   usage or accuracy metric. "10,000+ documents indexed" and "98.6% retrieval
   accuracy" would be invented — there is no such benchmark and the corpus is
   whatever the customer uploads. A platform that markets itself on never
   fabricating cannot open with fabricated numbers, so these count real,
   checkable capabilities instead.
   ───────────────────────────────────────────────────────────────────────── */
const STATS: { value: number; suffix?: string; label: string }[] = [
  { value: 100, suffix: "%", label: "Source-grounded answers" },
  { value: 3, label: "Retrieval methods combined" },
  { value: 5, label: "Grounded report types" },
  { value: 7, label: "Intelligence modules" },
];

const CAPABILITIES = [
  { icon: Network, title: "Knowledge graph", desc: "Entities and relationships extracted from your files.", float: [0, -9, 0], dur: 9 },
  { icon: Wrench, title: "Maintenance", desc: "Evidence-based RCA from real maintenance history.", float: [0, 8, 0], dur: 11 },
  { icon: ShieldCheck, title: "Compliance", desc: "Checked against standards your documents reference.", float: [0, -7, 0], dur: 12 },
  { icon: FileText, title: "Grounded reports", desc: "PDFs that cite the evidence behind every finding.", float: [0, 9, 0], dur: 10 },
];

/* Trust markers describe how the system works. "GDPR Ready" is deliberately
   absent — that is a regulatory assertion nobody has verified for this build. */
const TRUST = [
  { icon: Lock, label: "Role-based access" },
  { icon: FileCheck2, label: "Source-verified answers" },
  { icon: ShieldCheck, label: "Self-hosted processing" },
];

const ROLES = ["ENGINEER", "INSPECTOR", "ADMIN"] as const;

/**
 * Counts up to `value`, then holds it.
 *
 * Driven by React state rather than a MotionValue rendered as a motion child:
 * that approach server-renders the *initial* number as static text, and after
 * hydration the subscription does not reliably re-attach — leaving a permanent
 * "0" on screen. State also initialises to the real figure, so if the animation
 * never runs the correct number is shown rather than a stale zero, and the
 * cleanup snaps back so a stopped animation cannot strand a half-counted value.
 */
function StatNumber({ value }: { value: number }) {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(value);

  useEffect(() => {
    if (reduce) return; // state already holds the true figure
    const controls = animate(0, value, {
      duration: 1.1,
      ease: EASE,
      onUpdate: (v) => setShown(Math.round(v)),
      onComplete: () => setShown(value),
    });
    return () => { controls.stop(); setShown(value); };
  }, [value, reduce]);

  return <>{shown}</>;
}

export default function HomePage() {
  const { login, register, token, isLoading } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "ENGINEER" });
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoading && token) router.replace("/dashboard");
  }, [token, isLoading, router]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login({ email: form.email, password: form.password });
      } else {
        await register({
          email: form.email, password: form.password,
          full_name: form.full_name, role: form.role,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const isRegister = mode === "register";
  // 100ms cascade: logo → headline → sub → stats → cards → trust → login card.
  const step = (i: number) => ({
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.45, delay: i * 0.1, ease: EASE },
  });

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-canvas">
      {/* ── Photographic backdrop ──
          Small copy over this uses ink-secondary, never ink-tertiary: the
          tertiary token is ~2.6:1 on plain white and cannot reach AA at 11px
          no matter how strong the scrim is.
          The render is decorative, so it carries an empty alt and is hidden from
          assistive tech. The scrim above it is not optional styling: body copy
          sits on top, and unveiled the image drops text contrast below AA. It is
          weighted left (where the hero copy sits) and lighter through the middle
          so the graph render still reads. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 z-0">
        <Image
          src="/login-backdrop.png"
          alt=""
          fill
          priority
          sizes="100vw"
          className="object-cover object-center"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-white/96 via-white/72 to-white/88" />
        <div className="absolute inset-0 bg-gradient-to-b from-white/55 via-white/20 to-white/72" />
      </div>

      {/* ── Brand mark ──
          Anchored to the page rather than sitting in the hero column: the column
          is vertically centred, which dragged the logo down to the middle of the
          screen. A brand mark belongs in the corner. */}
      <motion.div
        {...step(0)}
        // Insets track the container padding at each breakpoint (px-5 / px-10).
        className="absolute left-5 top-6 z-20 flex items-center gap-2.5 lg:left-10 lg:top-8"
      >
        <div className="flex h-9 w-9 items-center justify-center rounded-ui-md bg-brand shadow-[0_8px_20px_-6px_rgba(91,94,247,0.6)]">
          <Brain className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold leading-tight text-ink">IndusMind</p>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-ink/70">
            Industrial Knowledge Intelligence
          </p>
        </div>
      </motion.div>

      {/* ── Left hero ── */}
      <aside className="relative z-10 hidden w-1/2 flex-col justify-center gap-6 px-10 py-8 lg:flex xl:w-[55%]">
        {/* The backdrop render is itself an isometric knowledge graph, so the
            hand-built <IndustrialAiScene /> that used to sit here would put a
            second graph on the same screen. The photo carries that motif now. */}

        <div className="max-w-xl">
          <motion.h1 {...step(2)} className="text-[30px] font-bold leading-[1.15] tracking-tight text-ink">
            Turn industrial documents into answers you can defend.
          </motion.h1>
          <motion.p {...step(3)} className="mt-2.5 max-w-lg text-[14px] leading-relaxed text-ink/80">
            SOPs, maintenance logs, inspections and audits become a queryable knowledge base —
            every answer cites the document it came from.
          </motion.p>

          {/* Verifiable capability stats */}
          <motion.ul {...step(4)} className="mt-5 grid grid-cols-2 gap-x-5 gap-y-3 sm:grid-cols-4">
            {STATS.map((s) => (
              <li key={s.label}>
                <p className="text-[24px] font-bold leading-none tracking-tight text-ink">
                  <StatNumber value={s.value} />
                  {s.suffix}
                </p>
                <p className="mt-1 text-[11px] font-semibold leading-snug text-ink/75">{s.label}</p>
              </li>
            ))}
          </motion.ul>

          {/* Floating glass capability cards */}
          <motion.ul {...step(5)} className="mt-5 grid grid-cols-2 gap-2.5">
            {CAPABILITIES.map((c) => {
              const Icon = c.icon;
              return (
                <motion.li
                  key={c.title}
                  animate={{ y: c.float }}
                  transition={{ duration: c.dur, repeat: Infinity, ease: "easeInOut" }}
                  whileHover={{ y: -6, transition: { duration: 0.2, ease: EASE } }}
                  className={cn(
                    "group rounded-ui-xl border border-white/60 bg-white/85 p-3 backdrop-blur-md",
                    "shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow duration-200",
                    "hover:shadow-[0_14px_40px_rgba(91,94,247,0.14)]"
                  )}
                >
                  <span className="inline-flex rounded-ui-sm bg-brand-subtle p-1.5 text-brand transition-transform duration-300 group-hover:rotate-6">
                    <Icon className="h-4 w-4" />
                  </span>
                  <p className="mt-2 text-xs font-bold text-ink">{c.title}</p>
                  <p className="mt-0.5 text-[11px] leading-relaxed text-ink-secondary">{c.desc}</p>
                </motion.li>
              );
            })}
          </motion.ul>
        </div>

        <motion.ul {...step(6)} className="mt-1 flex flex-wrap items-center gap-x-5 gap-y-2">
          {TRUST.map((t) => {
            const Icon = t.icon;
            return (
              <li key={t.label} className="flex items-center gap-1.5 text-[11px] font-semibold text-ink/75">
                <Icon className="h-3 w-3" /> {t.label}
              </li>
            );
          })}
        </motion.ul>
      </aside>

      {/* ── Right: auth ── */}
      <main className="relative z-10 flex flex-1 items-center justify-center px-5 py-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: [20, 0, 0] }}
          transition={{ duration: 0.5, delay: 0.5, ease: EASE }}
          className="w-full max-w-[400px]"
        >
          <motion.div
            // Gentle float, 6s — the card breathes rather than sits.
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 }}
            className={cn(
              "rounded-ui-xl border border-white/60 bg-white/85 p-7 backdrop-blur-xl",
              "shadow-[0_20px_60px_-12px_rgba(15,23,42,0.16)]"
            )}
          >
            {/* Small animated AI mark above the form */}
            <div className="mb-5 flex items-center gap-3">
              <motion.div
                animate={{ boxShadow: [
                  "0 8px 24px -8px rgba(91,94,247,0.45)",
                  "0 10px 30px -6px rgba(139,92,246,0.6)",
                  "0 8px 24px -8px rgba(91,94,247,0.45)",
                ] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="flex h-10 w-10 items-center justify-center rounded-ui-md bg-gradient-to-br from-brand to-ai-solid"
              >
                <Sparkles className="h-5 w-5 text-white" />
              </motion.div>
              <div>
                <h2 className="text-card font-bold leading-tight text-ink">
                  {isRegister ? "Create your account" : "Welcome back"}
                </h2>
                <p className="text-[11px] text-ink-tertiary">
                  {isRegister ? "Set up workspace access" : "Sign in to your workspace"}
                </p>
              </div>
            </div>

            {/* Mode switch */}
            <div className="grid grid-cols-2 gap-1 rounded-ui-md border border-line bg-subtle/80 p-1">
              {(["login", "register"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => { setMode(m); setError(""); }}
                  className={cn(
                    "rounded-ui-sm py-1.5 text-xs font-semibold transition-all",
                    mode === m ? "bg-surface text-ink shadow-e1" : "text-ink-tertiary hover:text-ink"
                  )}
                >
                  {m === "login" ? "Sign in" : "Register"}
                </button>
              ))}
            </div>

            <form onSubmit={handleSubmit} className="mt-5 space-y-3.5">
              {isRegister && (
                <FloatField id="name" label="Full name" icon={User} value={form.full_name}
                  onChange={set("full_name")} required autoComplete="name" />
              )}
              <FloatField id="email" label="Email" icon={Mail} type="email" value={form.email}
                onChange={set("email")} required autoComplete="email" />
              <FloatField
                id="password" label="Password" icon={Lock}
                type={showPwd ? "text" : "password"} value={form.password}
                onChange={set("password")} required
                autoComplete={isRegister ? "new-password" : "current-password"}
                trailing={
                  <button type="button" onClick={() => setShowPwd((s) => !s)}
                    aria-label={showPwd ? "Hide password" : "Show password"}
                    className="p-1 text-ink-tertiary transition-colors hover:text-brand">
                    {showPwd ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                }
              />

              {isRegister && (
                <div>
                  <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-tertiary">Role</p>
                  <div className="grid grid-cols-3 gap-1.5">
                    {ROLES.map((r) => (
                      <button key={r} type="button" onClick={() => setForm((f) => ({ ...f, role: r }))}
                        className={cn(
                          "rounded-ui-md border py-1.5 text-[11px] font-semibold transition-all",
                          form.role === r
                            ? "border-brand-line bg-brand-subtle text-brand shadow-e1"
                            : "border-line bg-surface text-ink-secondary hover:bg-subtle"
                        )}>
                        {r.charAt(0) + r.slice(1).toLowerCase()}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                  className="flex items-start gap-2 rounded-ui-md border border-danger/25 bg-danger-subtle px-3 py-2"
                  role="alert"
                >
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-danger" />
                  <p className="text-xs font-medium leading-relaxed text-danger">{error}</p>
                </motion.div>
              )}

              {/* Premium gradient CTA */}
              <motion.div whileHover={{ scale: 1.015 }} whileTap={{ scale: 0.98 }}
                transition={{ duration: 0.15, ease: EASE }}>
                <Button
                  type="submit"
                  loading={loading}
                  className={cn(
                    "w-full border-0 bg-gradient-to-r from-[#5B5EF7] to-[#7C6BFF] text-white",
                    "shadow-[0_8px_24px_-8px_rgba(91,94,247,0.55)]",
                    "transition-shadow duration-200 hover:shadow-[0_15px_40px_rgba(91,94,247,0.35)]"
                  )}
                >
                  {isRegister ? "Create account" : "Sign in"}
                </Button>
              </motion.div>
            </form>

            <p className="mt-5 text-center text-[11px] text-ink-tertiary">
              {isRegister ? "Already have an account?" : "Don't have an account?"}{" "}
              <button type="button"
                onClick={() => { setMode(isRegister ? "login" : "register"); setError(""); }}
                className="font-semibold text-brand hover:underline">
                {isRegister ? "Sign in" : "Register"}
              </button>
            </p>
          </motion.div>

          {/* Mobile trust row */}
          <ul className="mt-5 flex flex-wrap justify-center gap-x-4 gap-y-2 lg:hidden">
            {TRUST.map((t) => {
              const Icon = t.icon;
              return (
                <li key={t.label} className="flex items-center gap-1.5 text-[11px] font-semibold text-ink/75">
                  <Icon className="h-3 w-3" /> {t.label}
                </li>
              );
            })}
          </ul>
        </motion.div>
      </main>
    </div>
  );
}

/** Input with a floating label, purple focus border and soft glow. */
function FloatField({
  id, label, icon: Icon, trailing, value, ...props
}: {
  id: string;
  label: string;
  icon: React.ElementType;
  trailing?: React.ReactNode;
  value: string;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  const [focused, setFocused] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  const lifted = focused || value.length > 0;

  return (
    <div className="relative">
      <div
        className={cn(
          "flex items-center gap-2 rounded-ui-md border bg-surface px-3 transition-all duration-200",
          focused
            ? "border-brand shadow-[0_0_0_4px_rgba(91,94,247,0.12)]"
            : "border-line hover:border-line-strong"
        )}
      >
        <Icon className={cn("h-3.5 w-3.5 shrink-0 transition-colors", focused ? "text-brand" : "text-ink-tertiary")} />
        <div className="relative flex-1">
          <motion.label
            htmlFor={id}
            onClick={() => ref.current?.focus()}
            animate={{
              y: lifted ? -9 : 0,
              fontSize: lifted ? "10px" : "13px",
              color: focused ? "var(--color-brand)" : "var(--color-ink-tertiary)",
            }}
            transition={{ duration: 0.18, ease: EASE }}
            className="pointer-events-none absolute left-0 top-1/2 origin-left -translate-y-1/2 font-semibold"
          >
            {label}
          </motion.label>
          <input
            id={id}
            ref={ref}
            value={value}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            className="w-full bg-transparent pb-1.5 pt-4 text-[13px] text-ink outline-none"
            {...props}
          />
        </div>
        {trailing}
      </div>
    </div>
  );
}
