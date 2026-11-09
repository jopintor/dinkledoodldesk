"use client";

// App chrome shared by the agent and admin screens: left sidebar with nav items (Figma
// "Nav item" 3:132) and the signed-in user card.
import {
  BarChart3,
  BookOpen,
  Check,
  Inbox,
  LogOut,
  MessageSquare,
  ShieldCheck,
  SlidersHorizontal,
  Ticket,
  Wifi,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { Avatar, Badge, Logo, cx } from "@/components/ui";
import { IS_MOCK } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { initialsSubtitle } from "@/lib/format";
import type { User } from "@/lib/types";

export function UserCard({ user }: { user: User }) {
  const { signOut } = useAuth();
  const router = useRouter();
  return (
    <div className="flex items-center gap-3 rounded-md bg-card p-3">
      <Avatar kind="person" name={user.full_name} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-body font-semibold text-ink">{user.full_name}</p>
        <p className="truncate text-caption text-body">{initialsSubtitle(user)}</p>
      </div>
      <button
        type="button"
        aria-label="Sign out"
        title="Sign out"
        onClick={async () => {
          await signOut();
          router.replace("/login");
        }}
        className="rounded-sm p-1.5 text-body hover:bg-muted hover:text-ink"
      >
        <LogOut size={18} aria-hidden />
      </button>
    </div>
  );
}

type NavItem = { href?: string; label: string; icon: LucideIcon; badge?: string };

export function navFor(user: User, escalationCount?: number): NavItem[] {
  const queue = escalationCount ? ` · ${escalationCount}` : "";
  if (user.role === "admin") {
    return [
      { href: "/admin", label: "Dashboard", icon: BarChart3 },
      { href: "/agent", label: "Escalations", icon: Inbox },
      { href: "/admin/knowledge-base", label: "Knowledge base", icon: BookOpen },
      { href: "/admin#guardrails", label: "Guardrail log", icon: ShieldCheck },
      { href: "/admin#eval", label: "Eval runs", icon: Check },
      { label: "Settings", icon: SlidersHorizontal },
      { href: "/chat", label: "Chat as user", icon: MessageSquare },
    ];
  }
  return [
    { href: "/agent", label: `Escalation queue${queue}`, icon: Inbox },
    { label: "All tickets", icon: Ticket },
    { label: "Approvals", icon: Check },
    { href: "/admin/knowledge-base", label: "Knowledge base", icon: BookOpen },
    { label: "Service status", icon: Wifi },
  ];
}

export function AppShell({
  user,
  children,
  escalationCount,
}: {
  user: User;
  children: ReactNode;
  escalationCount?: number;
}) {
  const pathname = usePathname();
  const items = navFor(user, escalationCount);
  return (
    <div className="flex min-h-screen flex-1 flex-col lg:flex-row">
      <aside className="flex flex-col gap-6 border-line bg-muted px-5 py-5 lg:sticky lg:top-0 lg:h-screen lg:w-[248px] lg:shrink-0 lg:border-r">
        <div className="flex items-center justify-between">
          <Logo />
          {IS_MOCK && (
            <Badge tone="warning" className="lg:hidden">
              Mock API
            </Badge>
          )}
        </div>
        <nav aria-label="Main" className="no-scrollbar -mx-1 flex gap-1 overflow-x-auto px-1 lg:mx-0 lg:flex-col lg:overflow-visible lg:px-0">
          {items.map((item) => {
            const active = item.href && item.href.split("#")[0] === pathname && !item.href.includes("#");
            const content = (
              <>
                <item.icon size={20} aria-hidden />
                <span>{item.label}</span>
              </>
            );
            const cls = cx(
              "flex shrink-0 items-center gap-3 rounded-md px-3 py-2.5 text-body font-medium whitespace-nowrap",
              active ? "bg-soft font-semibold text-primary" : "text-body",
            );
            return item.href ? (
              <Link key={item.label} href={item.href} className={cx(cls, !active && "hover:bg-card hover:text-ink")} aria-current={active ? "page" : undefined}>
                {content}
              </Link>
            ) : (
              <span key={item.label} className={cx(cls, "cursor-not-allowed opacity-60")} title="Coming in a later sprint" aria-disabled>
                {content}
              </span>
            );
          })}
        </nav>
        <div className="hidden flex-1 lg:block" />
        {IS_MOCK && (
          <p className="hidden text-caption text-subtle lg:block" title="NEXT_PUBLIC_API_BASE_URL=/mock-api">
            Running on the built-in mock API
          </p>
        )}
        <div className="hidden lg:block">
          <UserCard user={user} />
        </div>
      </aside>
      <div className="min-w-0 flex-1">{children}</div>
      <div className="border-t border-line p-4 lg:hidden">
        <UserCard user={user} />
      </div>
    </div>
  );
}
