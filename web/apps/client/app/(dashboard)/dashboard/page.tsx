"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { StatCard } from "@/components/stat-card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ClipboardList,
  Clock,
  CheckCircle2,
  IndianRupee,
} from "lucide-react";
import type { Order, PaginatedResponse } from "@/types";

interface DashboardStats {
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  total_revenue: number;
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  confirmed: "bg-blue-100 text-blue-800",
  assigned: "bg-purple-100 text-purple-800",
  in_progress: "bg-indigo-100 text-indigo-800",
  sample_collected: "bg-cyan-100 text-cyan-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      const { data } = await api.get("/orders/stats/");
      return data;
    },
  });

  const { data: recentOrders, isLoading: ordersLoading } = useQuery<
    PaginatedResponse<Order>
  >({
    queryKey: ["recent-orders"],
    queryFn: async () => {
      const { data } = await api.get("/orders/", {
        params: { page_size: 10, ordering: "-created_at" },
      });
      return data;
    },
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your orders and activity.
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Orders"
          value={statsLoading ? "—" : (stats?.total_orders ?? 0)}
          icon={ClipboardList}
        />
        <StatCard
          title="Pending"
          value={statsLoading ? "—" : (stats?.pending_orders ?? 0)}
          icon={Clock}
        />
        <StatCard
          title="Completed"
          value={statsLoading ? "—" : (stats?.completed_orders ?? 0)}
          icon={CheckCircle2}
        />
        <StatCard
          title="Revenue"
          value={
            statsLoading
              ? "—"
              : `₹${(stats?.total_revenue ?? 0).toLocaleString("en-IN")}`
          }
          icon={IndianRupee}
        />
      </div>

      {/* Recent orders */}
      <div>
        <h2 className="mb-4 text-xl font-semibold">Recent Orders</h2>
        {ordersLoading ? (
          <p className="text-muted-foreground">Loading orders…</p>
        ) : !recentOrders?.results?.length ? (
          <p className="text-muted-foreground">No orders yet.</p>
        ) : (
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order #</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Patients</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentOrders.results.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-medium">
                      {order.order_number}
                    </TableCell>
                    <TableCell>
                      {new Date(order.created_at).toLocaleDateString("en-IN")}
                    </TableCell>
                    <TableCell>{order.patients.length}</TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={statusColors[order.status] ?? ""}
                      >
                        {order.status.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      ₹{order.total_amount.toLocaleString("en-IN")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}
