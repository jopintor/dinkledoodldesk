// Shared building blocks from the Figma "Style guide" page: Logo, Button, Status badge,
// Avatar, Citation chip, Quick question chip.
import { BookOpen, Headset, Sparkle } from "lucide-react";
import Image from "next/image";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import type { Citation } from "@/lib/types";

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

// ---------- Logo (Figma 3:10 Logo/Mark, 3:18 Logo/Full) ----------

export function LogoMark({ size = 40 }: { size?: number }) {
  // The SVG is 44×42: a 40×40 tile plus the yellow ball that hangs off the corner.
  return (
    <Image
      src="/brand/logo-mark.svg"
      alt=""
      width={Math.round(size * 1.1)}
      height={Math.round(size * 1.05)}
      className="shrink-0"
      style={{ marginRight: -size * 0.1, marginBottom: -size * 0.05 }}
      priority
    />
  );
}

export function Logo({ size = 40 }: { size?: number }) {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark size={size} />
      <span className="text-h2 text-ink">DinkDesk</span>
    </div>
  );
}

// ---------- Button (Figma 3:64: Variant × Size) ----------

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "lg" | "sm";
  icon?: ReactNode;
};

export function Button({ variant = "primary", size = "lg", icon, className, children, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      className={cx(
        "inline-flex shrink-0 items-center justify-center gap-2 font-semibold whitespace-nowrap transition-colors disabled:cursor-not-allowed disabled:opacity-60",
        size === "lg" ? "rounded-md px-5 py-3 text-body" : "rounded-sm px-3 py-2 text-label",
        variant === "primary" && "bg-primary text-white hover:bg-primary-hover",
        variant === "danger" && "bg-danger text-white hover:brightness-95",
        variant === "secondary" && "border border-line-strong bg-card text-primary hover:bg-softer",
        variant === "ghost" && "text-primary hover:bg-soft",
        className,
      )}
    >
      {icon}
      {children}
    </button>
  );
}

// ---------- Status badge (Figma 3:107, Tone) ----------

export type Tone = "brand" | "success" | "warning" | "danger" | "info" | "neutral";

const toneClass: Record<Tone, string> = {
  brand: "bg-soft text-primary",
  success: "bg-success-bg text-success",
  warning: "bg-warning-bg text-warning",
  danger: "bg-danger-bg text-danger",
  info: "bg-info-bg text-info",
  neutral: "bg-muted text-body",
};

export function Badge({
  tone = "brand",
  children,
  dot = true,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  dot?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cx(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-caption whitespace-nowrap",
        toneClass[tone],
        className,
      )}
    >
      {dot && <span aria-hidden className="size-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

// ---------- Avatar (Figma 3:27) ----------

export function Avatar({
  kind,
  name,
  size = 36,
}: {
  kind: "dinkdesk" | "agent" | "person";
  name?: string;
  size?: number;
}) {
  const style = { width: size, height: size };
  if (kind === "person") {
    const initials = (name ?? "?")
      .split(/\s+/)
      .map((p) => p[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
    return (
      <span
        style={style}
        className="inline-flex shrink-0 items-center justify-center rounded-full bg-ball-soft text-label text-ink"
        aria-hidden
      >
        {initials}
      </span>
    );
  }
  const Icon = kind === "agent" ? Headset : Sparkle;
  return (
    <span
      style={style}
      className={cx(
        "inline-flex shrink-0 items-center justify-center rounded-full",
        kind === "agent" ? "bg-info-bg text-info" : "bg-soft text-primary",
      )}
      aria-hidden
    >
      <Icon size={Math.round(size / 2)} strokeWidth={2} />
    </span>
  );
}

// ---------- Citation chip (Figma 3:113) ----------

export function citationLabel(c: Citation) {
  return `${c.doc_id} · ${c.title}${c.section ? ` › ${c.section}` : ""}`;
}

export function CitationChip({ citation, compact = false }: { citation: Citation; compact?: boolean }) {
  return (
    <span
      title={`${citation.doc_id} · ${citation.title}${citation.section ? ` › ${citation.section}` : ""}`}
      className="inline-flex max-w-full items-center gap-2 rounded-full border border-line bg-softer py-1 pr-3 pl-1"
    >
      <span className="inline-flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-caption text-white">
        {citation.n}
      </span>
      <BookOpen size={14} className="shrink-0 text-body" aria-hidden />
      <span className="truncate text-caption text-ink">
        {compact ? `${citation.doc_id} · ${citation.title}` : citationLabel(citation)}
      </span>
    </span>
  );
}

export function Sources({ citations, compact }: { citations: Citation[]; compact?: boolean }) {
  if (!citations.length) return null;
  return (
    <div className={cx("flex flex-wrap items-center gap-2", compact && "flex-col items-start")}>
      <span className="text-caption text-subtle">Sources</span>
      {citations.map((c) => (
        <CitationChip key={`${c.n}-${c.chunk_id}`} citation={c} compact={compact} />
      ))}
    </div>
  );
}

// ---------- Quick question chip (Figma 3:117) ----------

export function QuickChip({ children, onClick, disabled }: { children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex shrink-0 items-center gap-2 rounded-full border border-line-strong bg-card px-4 py-2 text-label text-ink transition-colors hover:bg-softer disabled:opacity-60"
    >
      <Sparkle size={14} className="text-primary" aria-hidden />
      {children}
    </button>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cx("inline-block size-4 animate-spin rounded-full border-2 border-current border-r-transparent", className)}
    />
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="rounded-md bg-danger-bg px-3 py-2 text-label font-medium text-danger">
      {children}
    </p>
  );
}

export function FullPageLoading() {
  return (
    <main className="flex min-h-screen flex-1 items-center justify-center text-primary">
      <Spinner className="size-6" />
      <span className="sr-only">Loading DinkDesk…</span>
    </main>
  );
}
