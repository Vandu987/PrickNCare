"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import api from "./api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface AuthUser {
  id: string;
  role: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

/* ------------------------------------------------------------------ */
/* JWT helpers (client-side decode — no verification)                   */
/* ------------------------------------------------------------------ */

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

function extractUser(token: string): AuthUser | null {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.sub !== "string") return null;
  return { id: payload.sub as string, role: (payload.role as string) ?? "user" };
}

/* ------------------------------------------------------------------ */
/* Token storage helpers                                               */
/* ------------------------------------------------------------------ */

function getStoredTokens() {
  if (typeof window === "undefined") return null;
  const access = localStorage.getItem("access_token");
  const refresh = localStorage.getItem("refresh_token");
  if (!access || !refresh) return null;
  return { access, refresh };
}

function storeTokens(access: string, refresh: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
  // Set a simple cookie so Next.js middleware can detect auth state
  document.cookie = "logged_in=1; path=/; max-age=604800; SameSite=Lax";
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  document.cookie = "logged_in=; path=/; max-age=0";
}

/* ------------------------------------------------------------------ */
/* Context                                                             */
/* ------------------------------------------------------------------ */

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const tokens = getStoredTokens();
    if (tokens) {
      const u = extractUser(tokens.access);
      setUser(u);
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post("/auth/login", { email, password });
    storeTokens(data.access_token, data.refresh_token);
    const u = extractUser(data.access_token);
    setUser(u);
  }, []);

  const logout = useCallback(async () => {
    try {
      const tokens = getStoredTokens();
      if (tokens) {
        const payload = decodeJwtPayload(tokens.access);
        if (payload) {
          await api.post("/auth/logout", {
            jti: payload.jti,
            user_id: payload.sub,
            refresh_token: tokens.refresh,
          });
        }
      }
    } catch {
      // best-effort
    } finally {
      clearTokens();
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      logout,
    }),
    [user, isLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
