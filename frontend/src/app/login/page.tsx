"use client";

// Figma screen 01 Login (node 5:2).
import { ArrowRight, Check, Lock, Mail, Shield, User as UserIcon } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button, ErrorNote, Logo, Spinner, cx } from "@/components/ui";
import { ApiError, IS_MOCK } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";

type Audience = "staff" | "member";

const FEATURES = [
  "Cited answers from 28 PickleHub IT guides",
  "Resets your StaffID password after an identity check",
  "Opens IT Help tickets for you – no forms",
];

const DEMO_ACCOUNTS = [
  { label: "Staff (Lea)", audience: "staff" as const, user: "lea.bautista", password: "dinkdesk" },
  { label: "IT agent (Kat)", audience: "staff" as const, user: "kat.mendoza", password: "dinkdesk" },
  { label: "Admin (Ramon)", audience: "staff" as const, user: "ramon.villareal", password: "dinkdesk" },
  { label: "Member (Carla)", audience: "member" as const, user: "carla.reyes@picklehub.example", password: "dinkdesk" },
];

/** StaffID usernames ("lea.bautista") become the account email the API expects. */
function toEmail(value: string) {
  const v = value.trim().toLowerCase();
  return v.includes("@") ? v : `${v}@picklehub.example`;
}

export default function LoginPage() {
  const auth = useAuth();
  const router = useRouter();
  const [audience, setAudience] = useState<Audience>("staff");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForgot, setShowForgot] = useState(false);

  useEffect(() => {
    if (auth.status === "authenticated") router.replace(homeFor(auth.user.role));
  }, [auth, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError(audience === "staff" ? "Enter your StaffID username and password." : "Enter your Member App email and password.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const user = await auth.signIn(toEmail(username), password, remember);
      router.replace(homeFor(user.role));
    } catch (err) {
      const e2 = err as ApiError;
      setError(
        e2.status === 401
          ? audience === "staff"
            ? "StaffID username or password is incorrect."
            : "Email or password is incorrect."
          : e2.message,
      );
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-1 bg-page">
      {/* Brand panel */}
      <section className="hidden w-1/2 flex-col gap-8 bg-soft p-16 lg:flex">
        <Logo />
        <div className="flex flex-col gap-5">
          <p className="text-overline text-primary">PickleHub Clubs · IT help desk</p>
          <h1 className="text-display text-ink">
            Soft shots for
            <br />
            hard IT problems.
          </h1>
          <p className="max-w-[520px] text-body-lg text-body">
            DinkDesk answers IT questions for PickleHub staff and members 24/7, shows where every answer comes from, and
            hands you to a real person when it isn&apos;t sure.
          </p>
          <ul className="flex flex-col gap-3">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-3 text-body font-semibold text-ink">
                <span className="inline-flex size-6 items-center justify-center rounded-full bg-primary text-white">
                  <Check size={14} strokeWidth={2.5} aria-hidden />
                </span>
                {f}
              </li>
            ))}
          </ul>
        </div>
        <div className="flex flex-col gap-4">
          <Image src="/brand/court.svg" alt="" width={520} height={200} priority />
          <p className="text-caption text-body">
            Need a person now? IT Service Desk · ext. 4357 · 7:00 AM – 10:00 PM daily
          </p>
        </div>
      </section>

      {/* Sign-in area */}
      <section className="flex w-full flex-col items-center px-4 py-10 sm:px-8 lg:w-1/2 lg:justify-start lg:pt-[148px]">
        <div className="mb-8 lg:hidden">
          <Logo />
        </div>
        <form
          onSubmit={onSubmit}
          noValidate
          className="flex w-full max-w-[480px] flex-col gap-6 rounded-xl border border-line bg-card p-6 shadow-card sm:p-10"
        >
          <div className="flex flex-col gap-2">
            <h2 className="text-h1 text-ink">Welcome back</h2>
            <p className="text-body-lg text-body">Sign in to chat with DinkDesk.</p>
          </div>

          <div role="tablist" aria-label="Who is signing in" className="grid grid-cols-2 gap-1 rounded-full bg-muted p-1">
            {(
              [
                ["staff", "Staff & IT", UserIcon],
                ["member", "Member", UserIcon],
              ] as const
            ).map(([key, label, Icon]) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={audience === key}
                onClick={() => {
                  setAudience(key);
                  setError(null);
                }}
                className={cx(
                  "flex items-center justify-center gap-2 rounded-full py-3 text-body font-semibold transition-colors",
                  audience === key ? "bg-card text-primary shadow-card" : "text-body hover:text-ink",
                )}
              >
                {key === "member" ? <PaddleIcon /> : <Icon size={16} aria-hidden />}
                {label}
              </button>
            ))}
          </div>

          <label className="flex flex-col gap-2">
            <span className="text-label text-ink">{audience === "staff" ? "StaffID username" : "Member App email"}</span>
            <span className="flex items-center gap-3 rounded-md border border-line-strong bg-card px-4 py-3 focus-within:border-2 focus-within:border-primary focus-within:px-[15px] focus-within:py-[11px]">
              {audience === "staff" ? (
                <UserIcon size={18} className="text-body" aria-hidden />
              ) : (
                <Mail size={18} className="text-body" aria-hidden />
              )}
              <input
                name="username"
                autoComplete="username"
                type={audience === "staff" ? "text" : "email"}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={audience === "staff" ? "e.g. lea.bautista" : "you@example.com"}
                className="w-full bg-transparent text-body-lg text-ink outline-none placeholder:text-subtle"
              />
            </span>
          </label>

          <label className="flex flex-col gap-2">
            <span className="text-label text-ink">Password</span>
            <span className="flex items-center gap-3 rounded-md border border-line-strong bg-card px-4 py-3 focus-within:border-2 focus-within:border-primary focus-within:px-[15px] focus-within:py-[11px]">
              <Lock size={18} className="text-body" aria-hidden />
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-transparent text-body-lg text-ink outline-none"
              />
            </span>
          </label>

          <div className="flex items-center justify-between gap-4">
            <label className="flex items-center gap-2 text-label font-medium text-ink">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="size-[18px] accent-primary"
              />
              Keep me signed in
            </label>
            <button
              type="button"
              onClick={() => setShowForgot((v) => !v)}
              className="text-label text-primary hover:underline"
            >
              Forgot password?
            </button>
          </div>

          {showForgot && (
            <p className="rounded-md bg-softer px-4 py-3 text-label font-medium text-body">
              {audience === "staff"
                ? "Reset it at id.picklehub.example/reset, or call the IT Service Desk at ext. 4357. Once you're in, DinkDesk can also reset it for you after an identity check."
                : "Tap “Forgot password” on the Member App sign-in screen. The reset link goes to your Member App email."}
            </p>
          )}

          {error && <ErrorNote>{error}</ErrorNote>}

          <Button type="submit" disabled={busy} className="w-full" icon={busy ? <Spinner /> : <ArrowRight size={18} aria-hidden />}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>

          <div className="flex gap-3 rounded-md bg-softer px-4 py-3 text-caption text-body">
            <Shield size={16} className="mt-0.5 shrink-0" aria-hidden />
            <p>
              Your role (staff, agent or admin) comes from your StaffID account, so you&apos;ll land on the right screen
              automatically. Members sign in with their PickleHub Member App email.
            </p>
          </div>

          <p className="text-center text-caption text-body">DinkDesk will never ask for your password inside the chat.</p>
        </form>

        {IS_MOCK && (
          <div className="mt-6 w-full max-w-[480px] rounded-md border border-dashed border-line-strong px-4 py-3 text-caption text-body">
            <p className="mb-2 font-semibold text-ink">Mock API – demo accounts (password “dinkdesk”)</p>
            <div className="flex flex-wrap gap-2">
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.user}
                  type="button"
                  onClick={() => {
                    setAudience(a.audience);
                    setUsername(a.user);
                    setPassword(a.password);
                    setError(null);
                  }}
                  className="rounded-full border border-line bg-card px-3 py-1 text-ink hover:bg-softer"
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}

/** Figma icon/paddle (2:344), used on the Member tab. */
function PaddleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 3c4 0 7 2.6 7 7s-3 7-7 7-7-2.6-7-7 3-7 7-7Z" />
      <path d="M10.5 17v4h3v-4" />
    </svg>
  );
}
