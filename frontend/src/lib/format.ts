import type { Tone } from "@/components/ui";
import type { Priority, Role, ServiceState, TicketStatus } from "./types";

export function formatTime(iso: string | Date) {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export function formatClock(iso: string) {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function formatDate(iso: string, withYearIfOld = true) {
  const d = new Date(iso);
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  if (withYearIfOld && d.getFullYear() < new Date().getFullYear()) opts.year = "numeric";
  return d.toLocaleDateString("en-US", opts);
}

export function minutesLabel(seconds: number) {
  const m = Math.max(0, Math.round(seconds / 60));
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return `${h} h ${m % 60} min`;
}

export const SERVICE_STATE: Record<ServiceState, { label: string; tone: Tone }> = {
  operational: { label: "Operational", tone: "success" },
  degraded_performance: { label: "Delayed", tone: "warning" },
  partial_outage: { label: "Partial outage", tone: "warning" },
  major_outage: { label: "Outage", tone: "danger" },
  maintenance: { label: "Maintenance", tone: "info" },
};

export const TICKET_STATUS: Record<TicketStatus, { label: string; tone: Tone }> = {
  open: { label: "Open", tone: "warning" },
  in_progress: { label: "In progress", tone: "warning" },
  waiting_on_user: { label: "Pending", tone: "warning" },
  escalated: { label: "Escalated", tone: "info" },
  resolved: { label: "Resolved", tone: "success" },
  closed: { label: "Closed", tone: "neutral" },
};

export const PRIORITY_TONE: Record<Priority, Tone> = {
  P1: "danger",
  P2: "warning",
  P3: "info",
  P4: "neutral",
};

export const CATEGORY_LABEL: Record<string, string> = {
  company: "Company",
  "accounts-access": "Accounts & access",
  network: "Network",
  "pos-payments": "POS & payments",
  "member-app-booking": "Member app & booking",
  policy: "Policy",
  security: "Security",
  "support-process": "Support process",
};

export const ROLE_LABEL: Record<Role, string> = {
  member: "Member",
  staff: "Staff",
  agent: "IT Service Desk",
  admin: "Admin",
};

export function audienceLabel(roles: Role[]) {
  if (["member", "staff", "agent", "admin"].every((r) => roles.includes(r as Role))) return "everyone";
  return roles.join(" · ");
}

export function initialsSubtitle(user: { job_title?: string | null; role: Role; club_code?: string | null }) {
  if (user.role === "agent") return user.job_title ?? ROLE_LABEL.agent;
  if (user.role === "admin") return [user.job_title, "Admin"].filter(Boolean).join(" · ");
  return [user.job_title, ROLE_LABEL[user.role], user.club_code].filter(Boolean).join(" · ");
}
