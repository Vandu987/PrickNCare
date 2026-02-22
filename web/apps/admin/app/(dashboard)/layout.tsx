"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "@/components/admin/admin-layout";
import { useAuth } from "@/contexts/auth-context";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    console.log("[DashboardLayout] isAuthenticated:", isAuthenticated);
    if (!isAuthenticated) {
      console.log("[DashboardLayout] not authenticated → router.replace('/login')");
      router.replace("/login");
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    console.log("[DashboardLayout] render → returning null (blank)");
    return null;
  }

  return <AdminLayout>{children}</AdminLayout>;
}
