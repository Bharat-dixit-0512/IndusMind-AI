"use client";

import Link from "next/link";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronsUpDown, LogOut, Settings } from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { Avatar } from "@/components/ui";
import { cn } from "@/lib/utils";

/**
 * Sidebar account block.
 *
 * Everything shown here comes from the authenticated user record — name, email
 * and role. There are deliberately no "Billing", "Notifications" or "Upgrade"
 * entries: those pages do not exist, and a menu that lists routes leading
 * nowhere is worse than a short menu.
 *
 * Radix owns the hard parts — focus trapping, arrow-key roving, Escape,
 * outside-click and the ARIA menu semantics — so keyboard users get a real
 * menu rather than a div that happens to open.
 */
export default function AccountMenu({ collapsed = false }: { collapsed?: boolean }) {
  const { user, logout } = useAuth();

  const name = user?.name?.trim() || "Account";
  const email = user?.email?.trim();
  const role = user?.role;

  const itemClass = cn(
    "flex cursor-pointer select-none items-center gap-2.5 rounded-ui-sm px-2 py-1.5",
    "text-[13px] font-medium text-ink outline-none transition-colors",
    "data-[highlighted]:bg-subtle data-[highlighted]:text-ink"
  );

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          aria-label={`Account menu for ${name}`}
          className={cn(
            "group flex w-full items-center gap-2.5 rounded-ui-md p-1.5 text-left transition-colors",
            "outline-none focus-visible:ring-2 focus-visible:ring-brand/70",
            "hover:bg-white/[0.06] data-[state=open]:bg-white/[0.08]",
            collapsed && "justify-center"
          )}
        >
          <Avatar name={user?.name} email={user?.email} size={collapsed ? "sm" : "md"} />
          {!collapsed && (
            <>
              <span className="min-w-0 flex-1 leading-tight">
                <span className="block truncate text-xs font-bold text-white">{name}</span>
                <span className="block truncate text-[10px] font-semibold uppercase tracking-wide text-sidebar-ink">
                  {role ?? "—"}
                </span>
              </span>
              <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-sidebar-ink transition-colors group-hover:text-white" />
            </>
          )}
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          // Opens upward: the trigger sits at the bottom of the viewport.
          side={collapsed ? "right" : "top"}
          align={collapsed ? "end" : "start"}
          sideOffset={8}
          collisionPadding={12}
          className={cn(
            "ui-menu-content z-50 rounded-ui-lg border border-line bg-surface p-1.5 shadow-e4",
            // Expanded: match the trigger exactly so the panel sits flush inside
            // the sidebar rail instead of spilling over into the content area.
            // Collapsed: the trigger is just an avatar, so use a readable width.
            collapsed
              ? "w-60"
              : "w-[var(--radix-dropdown-menu-trigger-width)]"
          )}
        >
          {/* Identity header — the email is the part users actually check when
              they have more than one account. */}
          <div className="flex items-center gap-2.5 px-2 py-2">
            <Avatar name={user?.name} email={user?.email} size="lg" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-bold leading-tight text-ink">{name}</p>
              {email && (
                <p className="truncate text-[11px] leading-tight text-ink-secondary">{email}</p>
              )}
              {role && (
                <span className="mt-1 inline-flex items-center rounded-full bg-brand-subtle px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-brand">
                  {role}
                </span>
              )}
            </div>
          </div>

          <DropdownMenu.Separator className="my-1 h-px bg-line" />

          <DropdownMenu.Item asChild className={itemClass}>
            <Link href="/settings">
              <Settings className="h-3.5 w-3.5 text-ink-tertiary" />
              Settings
            </Link>
          </DropdownMenu.Item>

          <DropdownMenu.Separator className="my-1 h-px bg-line" />

          <DropdownMenu.Item
            onSelect={logout}
            className={cn(
              itemClass,
              "text-danger data-[highlighted]:bg-danger-subtle data-[highlighted]:text-danger"
            )}
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
