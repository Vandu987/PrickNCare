"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { decodeToken, logout as doLogout, type JwtPayload, type UserRole } from "@/lib/auth";

interface AuthContextValue {
  user: JwtPayload | null;
  isAuthenticated: boolean;
  hasRole: (role: UserRole | UserRole[]) => boolean;
  logout: () => void;
  refresh: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isAuthenticated: false,
  hasRole: () => false,
  logout: () => {},
  refresh: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<JwtPayload | null>(null);

  const refresh = useCallback(() => {
    const decoded = decodeToken();
    console.log("[AuthProvider] refresh() → user:", decoded ? decoded.email : "null");
    setUser(decoded);
  }, []);

  useEffect(() => {
    console.log("[AuthProvider] mounted, calling refresh()");
    refresh();
    const onStorage = (e: StorageEvent) => {
      if (e.key === "access_token") refresh();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [refresh]);

  const hasRole = useCallback(
    (role: UserRole | UserRole[]) => {
      if (!user) return false;
      const roles = Array.isArray(role) ? role : [role];
      return roles.includes(user.role);
    },
    [user]
  );

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, hasRole, logout: doLogout, refresh }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
