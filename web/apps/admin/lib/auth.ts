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
  return localStorage.getItem("access_token");
}

export function decodeToken(): JwtPayload | null {
  const token = getToken();
  if (!token) return null;
  try {
    const decoded = jwtDecode<JwtPayload>(token);
    if (decoded.exp * 1000 < Date.now()) {
      return null;
    }
    return decoded;
  } catch {
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
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  document.cookie = "access_token=; path=/; max-age=0";
  window.location.href = "/login";
}
