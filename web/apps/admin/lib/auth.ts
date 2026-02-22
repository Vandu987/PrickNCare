import { jwtDecode } from "jwt-decode";

export type UserRole = "super_admin" | "admin" | "lab_manager" | "phlebotomist" | "support";

export interface JwtPayload {
  sub: string;
  email: string;
  role: UserRole;
  name: string;
  exp: number;
  iat: number;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("access_token");
  console.log("[auth] getToken →", token ? `found (${token.substring(0, 20)}...)` : "null");
  return token;
}

export function decodeToken(): JwtPayload | null {
  const token = getToken();
  if (!token) {
    console.log("[auth] decodeToken → no token in localStorage");
    return null;
  }
  try {
    const decoded = jwtDecode<JwtPayload>(token);
    const isExpired = decoded.exp * 1000 < Date.now();
    console.log("[auth] decodeToken →", isExpired ? "token EXPIRED" : `valid, user=${decoded.email}, role=${decoded.role}`);
    if (isExpired) return null;
    return decoded;
  } catch (e) {
    console.log("[auth] decodeToken → decode ERROR:", e);
    return null;
  }
}

export function hasRole(required: UserRole | UserRole[]): boolean {
  const payload = decodeToken();
  if (!payload) return false;
  const roles = Array.isArray(required) ? required : [required];
  return roles.includes(payload.role);
}

export function logout() {
  console.log("[auth] logout() called");
  console.log("[auth] localStorage before:", {
    access_token: localStorage.getItem("access_token")?.substring(0, 20),
    refresh_token: localStorage.getItem("refresh_token")?.substring(0, 20),
  });
  console.log("[auth] cookie before:", document.cookie.substring(0, 100));

  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  document.cookie = "access_token=; path=/; max-age=0";

  console.log("[auth] cookie after clear:", document.cookie.substring(0, 100));
  console.log("[auth] redirecting to /login...");
  window.location.href = "/login";
}
