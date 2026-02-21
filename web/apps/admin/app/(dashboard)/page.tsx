"use client";

import { useAuth } from "@/contexts/auth-context";
import { CalendarDays, Users, TestTube, TrendingUp } from "lucide-react";

const stats = [
  { title: "Total Bookings", value: "—", icon: CalendarDays, color: "text-blue-600 bg-blue-100" },
  { title: "Active Patients", value: "—", icon: Users, color: "text-green-600 bg-green-100" },
  { title: "Phlebotomists", value: "—", icon: TestTube, color: "text-purple-600 bg-purple-100" },
  { title: "Revenue (MTD)", value: "—", icon: TrendingUp, color: "text-orange-600 bg-orange-100" },
];

export default function DashboardPage() {
  const { user } = useAuth();

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

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.title} className="rounded-lg border bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">{stat.title}</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
              <div className={`rounded-full p-3 ${stat.color}`}>
                <stat.icon className="h-5 w-5" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
