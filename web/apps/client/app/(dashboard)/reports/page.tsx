"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ClipboardList,
  CheckCircle2,
  IndianRupee,
  Download,
  BarChart3,
  TrendingUp,
  PieChart as PieChartIcon,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
} from "recharts";

// ── Types ──

interface DailyCollection {
  date: string;
  total_orders: number;
  completed_orders: number;
  total_amount: number;
}

interface RevenueData {
  date: string;
  revenue: number;
}

interface ClientWiseData {
  client_name: string;
  total_orders: number;
  total_revenue: number;
}

// ── Helpers ──

function formatDate(d: Date): string {
  return d.toISOString().split("T")[0];
}

function getDefaultRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return { from: formatDate(from), to: formatDate(to) };
}

const STATUS_COLORS = [
  "#6366f1", // indigo
  "#f59e0b", // amber
  "#10b981", // emerald
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#f97316", // orange
];

const TABS = ["Overview", "Orders", "Revenue"] as const;
type Tab = (typeof TABS)[number];

// ── Component ──

export default function ReportsPage() {
  const defaultRange = useMemo(getDefaultRange, []);
  const [dateFrom, setDateFrom] = useState(defaultRange.from);
  const [dateTo, setDateTo] = useState(defaultRange.to);
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  const queryParams = { date_from: dateFrom, date_to: dateTo };

  const { data: dailyData, isLoading: dailyLoading } = useQuery<
    DailyCollection[]
  >({
    queryKey: ["reports-daily", dateFrom, dateTo],
    queryFn: async () => {
      const { data } = await api.get("/reports/daily-collection", {
        params: queryParams,
      });
      return Array.isArray(data) ? data : data.results ?? [];
    },
  });

  const { data: revenueData, isLoading: revenueLoading } = useQuery<
    RevenueData[]
  >({
    queryKey: ["reports-revenue", dateFrom, dateTo],
    queryFn: async () => {
      const { data } = await api.get("/reports/revenue", {
        params: queryParams,
      });
      return Array.isArray(data) ? data : data.results ?? [];
    },
  });

  const { data: clientData, isLoading: clientLoading } = useQuery<
    ClientWiseData[]
  >({
    queryKey: ["reports-client", dateFrom, dateTo],
    queryFn: async () => {
      const { data } = await api.get("/reports/client-wise", {
        params: queryParams,
      });
      return Array.isArray(data) ? data : data.results ?? [];
    },
  });

  // Derived stats
  const totals = useMemo(() => {
    if (!dailyData) return { orders: 0, completed: 0, revenue: 0 };
    return dailyData.reduce(
      (acc, d) => ({
        orders: acc.orders + d.total_orders,
        completed: acc.completed + d.completed_orders,
        revenue: acc.revenue + d.total_amount,
      }),
      { orders: 0, completed: 0, revenue: 0 }
    );
  }, [dailyData]);

  // Status breakdown for pie chart (from client-wise data)
  const clientPieData = useMemo(() => {
    if (!clientData) return [];
    return clientData.slice(0, 7).map((c) => ({
      name: c.client_name,
      value: c.total_orders,
    }));
  }, [clientData]);

  // Orders over time chart data
  const ordersChartData = useMemo(() => {
    if (!dailyData) return [];
    return dailyData.map((d) => ({
      date: new Date(d.date).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
      }),
      orders: d.total_orders,
      completed: d.completed_orders,
    }));
  }, [dailyData]);

  // Revenue chart data
  const revenueChartData = useMemo(() => {
    if (!revenueData) return [];
    return revenueData.map((d) => ({
      date: new Date(d.date).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
      }),
      revenue: d.revenue,
    }));
  }, [revenueData]);

  const isLoading = dailyLoading || revenueLoading || clientLoading;

  async function handleExport() {
    try {
      const { data } = await api.get("/reports/export", {
        params: queryParams,
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${dateFrom}_${dateTo}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      // silently fail — could add toast
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground">
            Analyze orders, revenue, and performance.
          </p>
        </div>
        <Button onClick={handleExport} variant="outline" className="gap-2">
          <Download className="h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Date range picker */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium whitespace-nowrap">From</label>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-auto"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium whitespace-nowrap">To</label>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-auto"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-muted p-1">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Summary stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          title="Total Orders"
          value={isLoading ? "—" : totals.orders}
          icon={ClipboardList}
        />
        <StatCard
          title="Completed"
          value={isLoading ? "—" : totals.completed}
          icon={CheckCircle2}
        />
        <StatCard
          title="Revenue"
          value={
            isLoading
              ? "—"
              : `₹${totals.revenue.toLocaleString("en-IN")}`
          }
          icon={IndianRupee}
        />
      </div>

      {/* Tab content */}
      {(activeTab === "Overview" || activeTab === "Orders") && (
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <BarChart3 className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">Orders Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="py-12 text-center text-muted-foreground">
                Loading chart…
              </p>
            ) : ordersChartData.length === 0 ? (
              <p className="py-12 text-center text-muted-foreground">
                No data for the selected period.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={ordersChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip />
                  <Legend />
                  <Bar
                    dataKey="orders"
                    name="Total Orders"
                    fill="#6366f1"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="completed"
                    name="Completed"
                    fill="#10b981"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      )}

      {(activeTab === "Overview" || activeTab === "Revenue") && (
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">Revenue Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="py-12 text-center text-muted-foreground">
                Loading chart…
              </p>
            ) : revenueChartData.length === 0 ? (
              <p className="py-12 text-center text-muted-foreground">
                No data for the selected period.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={revenueChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip
                    formatter={(value) =>
                      `₹${Number(value).toLocaleString("en-IN")}`
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="revenue"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "Overview" && (
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <PieChartIcon className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">
              Client-wise Order Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="py-12 text-center text-muted-foreground">
                Loading chart…
              </p>
            ) : clientPieData.length === 0 ? (
              <p className="py-12 text-center text-muted-foreground">
                No data for the selected period.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <PieChart>
                  <Pie
                    data={clientPieData}
                    cx="50%"
                    cy="50%"
                    outerRadius={120}
                    innerRadius={60}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) =>
                      `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`
                    }
                  >
                    {clientPieData.map((_, i) => (
                      <Cell
                        key={i}
                        fill={STATUS_COLORS[i % STATUS_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
