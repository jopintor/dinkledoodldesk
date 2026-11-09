"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { ApiError, getMe, login, logout, setAuthToken } from "./api";
import type { Role, User } from "./types";

const TOKEN_KEY = "dinkdesk.token";

type AuthState =
  | { status: "loading"; user: null; permissions: string[] }
  | { status: "anonymous"; user: null; permissions: string[] }
  | { status: "authenticated"; user: User; permissions: string[] };

type AuthContextValue = AuthState & {
  signIn: (email: string, password: string, remember: boolean) => Promise<User>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

/** Where each role lands after signing in. */
export function homeFor(role: Role): string {
  if (role === "agent") return "/agent";
  if (role === "admin") return "/admin";
  return "/chat";
}

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string | null, remember = false) {
  try {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    if (token) (remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, token);
  } catch {
    // storage blocked (private mode): the session just won't survive a reload
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading", user: null, permissions: [] });

  useEffect(() => {
    const token = readToken();
    if (!token) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time read of browser storage
      setState({ status: "anonymous", user: null, permissions: [] });
      return;
    }
    setAuthToken(token);
    getMe()
      .then(({ user, permissions }) => setState({ status: "authenticated", user, permissions }))
      .catch(() => {
        setAuthToken(null);
        storeToken(null);
        setState({ status: "anonymous", user: null, permissions: [] });
      });
  }, []);

  const signIn = useCallback(async (email: string, password: string, remember: boolean) => {
    const res = await login(email, password);
    setAuthToken(res.access_token);
    try {
      const { user, permissions } = await getMe();
      storeToken(res.access_token, remember);
      setState({ status: "authenticated", user, permissions });
      return user;
    } catch (err) {
      setAuthToken(null);
      throw err instanceof ApiError ? err : new ApiError(0, "ERROR", "Signed in, but couldn't load your profile.");
    }
  }, []);

  const signOut = useCallback(async () => {
    try {
      await logout();
    } catch {
      // the token is discarded either way
    }
    setAuthToken(null);
    storeToken(null);
    setState({ status: "anonymous", user: null, permissions: [] });
  }, []);

  const value = useMemo(() => ({ ...state, signIn, signOut }), [state, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/**
 * Guards a page: sends anonymous visitors to /login and people without one of `roles` to
 * their own home. Returns the user once it is allowed to render.
 */
export function useRequireRole(roles: Role[]): User | null {
  const auth = useAuth();
  const router = useRouter();
  const allowed = auth.status === "authenticated" && roles.includes(auth.user.role);

  useEffect(() => {
    if (auth.status === "anonymous") router.replace("/login");
    else if (auth.status === "authenticated" && !roles.includes(auth.user.role)) router.replace(homeFor(auth.user.role));
  }, [auth, roles, router]);

  return allowed ? auth.user : null;
}
