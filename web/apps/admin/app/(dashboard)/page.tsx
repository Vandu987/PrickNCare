"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/auth-context";
import api from "@/lib/api";
import { StatCard } from "@/components/dashboard/stat-card";
import { RecentOrdersTable, type RecentOrder } from "@/components/dashboard/recent-orders-table";
import { PhlebotomistMap } from "@/components/dashboard/phlebotomist-map";
import {
  ShoppingCart,
  CheckCircle2,
  Clock,
  IndianRupee,
  Activity,
} from "lucide-react";

interface DashboardStats {
  total_orders_today: number;
  completed_orders: number;
  pending_orders: number;
  revenue_today: number;
  active_phlebotomists: number;
  recent_orders: RecentOrder[];
  phlebotomist_locations: {
    id: string;
    name: string;
    lat: number;
    lng: number;
    status: "active" | "idle" | "offline";
  }[];
}

async function fetchDashboard(): Promise<DashboardStats> {
  try {
    const { data } = await api.get<DashboardStats>("/reports/dashboard");
    return data;
  } catch {
    // Stub data when API is not available
    return {
      total_orders_today: 0,
      completed_orders: 0,
      pending_orders: 0,
      revenue_today: 0,
      active_phlebotomists: 0,
      recent_orders: [],
      phlebotomist_locations: [],
    };
  }
}

export default function DashboardPage() {
  const { user } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: fetchDashboard,
    refetchInterval: 30_000,
  });

  const stats = [
    {
      title: "Total Orders Today",
      value: data?.total_orders_today ?? 0,
      icon: ShoppingCart,
      color: "text-blue-600 bg-blue-100",
    },
    {
      title: "Completed",
      value: data?.completed_orders ?? 0,
      icon: CheckCircle2,
      color: "text-green-600 bg-green-100",
    },
    {
      title: "Pending",
      value: data?.pending_orders ?? 0,
      icon: Clock,
      color: "text-yellow-600 bg-yellow-100",
    },
    {
      title: "Revenue Today",
      value: `₹${(data?.revenue_today ?? 0).toLocaleString("en-IN")}`,
      icon: IndianRupee,
      color: "text-orange-600 bg-orange-100",
    },
    {
      title: "Active Phlebotomists",
      value: data?.active_phlebotomists ?? 0,
      icon: Activity,
      color: "text-purple-600 bg-purple-100",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back{user?.name ? `, ${user.name}` : ""}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Here&apos;s what&apos;s happening with your service today.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {stats.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={isLoading} />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <RecentOrdersTable
            orders={data?.recent_orders ?? []}
            isLoading={isLoading}
          />
        </div>
        <div className="lg:col-span-2">
          <PhlebotomistMap
            locations={data?.phlebotomist_locations}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
}
