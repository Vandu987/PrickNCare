"use client";

import React, { useState } from "react";
import { Droplets } from "lucide-react";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { refresh } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      // Check role — only admins allowed
      try {
        const payload = JSON.parse(atob(data.access_token.split('.')[1]));
        if (!['super_admin', 'SUPER_ADMIN', 'city_admin', 'CITY_ADMIN', 'admin'].includes(payload.role)) {
          setError("Access denied. This portal is for administrators only. Clients should use app.prickncare.com");
          setLoading(false);
          return;
        }
      } catch { /* proceed if decode fails */ }
      localStorage.setItem("access_token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("refresh_token", data.refresh_token);
      }
      document.cookie = `access_token=${data.access_token}; path=/; max-age=86400`;
      refresh();
      const params = new URLSearchParams(window.location.search);
      window.location.href = params.get("redirect") || "/";
    } catch {
      setError("Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border bg-white p-8 shadow-sm">
      <div className="mb-6 flex flex-col items-center">
        <Droplets className="h-12 w-12 text-primary-600" />
        <h1 className="mt-4 text-2xl font-bold">PricknCare Admin</h1>
        <p className="mt-1 text-sm text-gray-500">Sign in to your account</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>
        )}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
