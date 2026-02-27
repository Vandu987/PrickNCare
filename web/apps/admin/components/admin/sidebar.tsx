"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  CalendarDays,
  TestTube,
  MapPin,
  Settings,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Droplets,
  Building2,
  FlaskConical,
  Receipt,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";
import type { UserRole } from "@/lib/auth";

interface NavItem {
  title: string;
  href: string;
  icon: React.ElementType;
  roles?: UserRole[];
}

/*
 * Role-based visibility:
 *   super_admin  → everything
 *   admin        → dashboard, bookings, phlebotomists, service-areas, accessioning, reconciliation, reports, clients, patients
 *   lab_manager  → dashboard, bookings, phlebotomists, service-areas, accessioning, reconciliation, reports
 *   support      → dashboard, bookings, reports
 *   phlebotomist → dashboard, bookings (own), reports (own)
 */
const navItems: NavItem[] = [
  { title: "Dashboard", href: "/", icon: LayoutDashboard },
  { title: "Bookings", href: "/bookings", icon: CalendarDays },
  { title: "Clients", href: "/clients", icon: Building2, roles: ["super_admin", "admin"] },
  { title: "Patients", href: "/patients", icon: Users, roles: ["super_admin", "admin"] },
  { title: "Phlebotomists", href: "/phlebotomists", icon: TestTube, roles: ["super_admin", "admin", "lab_manager"] },
  { title: "Service Areas", href: "/service-areas", icon: MapPin, roles: ["super_admin", "admin", "lab_manager"] },
  { title: "Accessioning", href: "/accessioning", icon: FlaskConical, roles: ["super_admin", "admin", "lab_manager"] },
  { title: "Reconciliation", href: "/reconciliation", icon: Receipt, roles: ["super_admin", "admin", "lab_manager"] },
  { title: "Reports", href: "/reports", icon: BarChart3 },
  { title: "Settings", href: "/settings", icon: Settings, roles: ["super_admin", "admin"] },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const pathname = usePathname();
  const { hasRole } = useAuth();

  const filteredItems = navItems.filter(
    (item) => !item.roles || hasRole(item.roles)
  );

  return (
    <aside
      className={cn(
        "flex flex-col border-r bg-white transition-all duration-300",
        // Mobile: fixed overlay sidebar
        "max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:z-50 max-lg:w-64",
        mobileOpen ? "max-lg:translate-x-0" : "max-lg:-translate-x-full",
        // Desktop
        collapsed ? "lg:w-16" : "lg:w-64"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b px-4">
        <div className="flex items-center">
          <Droplets className="h-8 w-8 text-primary-600 shrink-0" />
          {!collapsed && (
            <span className="ml-2 text-lg font-bold text-gray-900">PricknCare</span>
          )}
        </div>
        {/* Mobile close button */}
        {onMobileClose && (
          <button
            onClick={onMobileClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 p-2">
        {filteredItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onMobileClose}
              className={cn(
                "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary-50 text-primary-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
                collapsed && "lg:justify-center lg:px-2"
              )}
              title={collapsed ? item.title : undefined}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span className="ml-3">{item.title}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Toggle */}
      <div className="border-t p-2">
        <button
          onClick={onToggle}
          className="flex w-full items-center justify-center rounded-md p-2 text-gray-400 hover:bg-gray-50 hover:text-gray-600"
        >
          {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </button>
      </div>
    </aside>
  );
}
