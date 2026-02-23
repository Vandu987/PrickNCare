"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ColumnDef } from "@tanstack/react-table";
import {
  Search,
  MoreHorizontal,
  Eye,
  UserPlus,
  Calendar,
  Filter,
  CheckSquare,
} from "lucide-react";
import api from "@/lib/api";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

// ── Types ──────────────────────────────────────────────

interface Patient {
  id: string;
  name: string;
  phone: string;
}

interface Client {
  id: string;
  name: string;
}

interface Phlebotomist {
  id: string;
  name: string;
  phone: string;
}

interface Zone {
  id: string;
  name: string;
}

interface Booking {
  id: string;
  booking_id: string;
  patient: Patient;
  client: Client;
  phlebotomist: Phlebotomist | null;
  scheduled_date: string;
  scheduled_time: string;
  status: string;
  priority: "normal" | "urgent" | "stat";
  city: string;
  zone: Zone | null;
  total_amount: number;
  created_at: string;
}

interface BookingsResponse {
  items: Booking[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface PhlebotomistOption {
  id: string;
  name: string;
  phone: string;
  zones: { id: string; name: string }[];
}

// ── API ────────────────────────────────────────────────

async function fetchBookings(params: {
  page: number;
  search: string;
  status: string;
  client_id: string;
  phlebotomist_id: string;
  city: string;
  date_from: string;
  date_to: string;
  priority: string;
}): Promise<BookingsResponse> {
  const query = new URLSearchParams();
  query.set("page", String(params.page));
  query.set("page_size", "20");
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.client_id) query.set("client_id", params.client_id);
  if (params.phlebotomist_id) query.set("phlebotomist_id", params.phlebotomist_id);
  if (params.city) query.set("city", params.city);
  if (params.date_from) query.set("date_from", params.date_from);
  if (params.date_to) query.set("date_to", params.date_to);
  if (params.priority) query.set("priority", params.priority);
  const { data } = await api.get(`/orders?${query.toString()}`);
  return data.data ?? data;
}

async function fetchPhlebotomists(): Promise<{ data: PhlebotomistOption[] }> {
  const { data } = await api.get("/phlebotomists?status=active");
  return data;
}

async function fetchClients(): Promise<{ items: Client[] }> {
  const { data } = await api.get("/clients?page_size=100&status=active");
  return data.data ?? data;
}

async function assignPhlebotomist(orderId: string, phlebotomistId: string) {
  const { data } = await api.post(`/orders/${orderId}/assign`, {
    phlebotomist_id: phlebotomistId,
  });
  return data;
}

async function bulkAssignPhlebotomist(orderIds: string[], phlebotomistId: string) {
  const { data } = await api.post("/orders/bulk-assign", {
    order_ids: orderIds,
    phlebotomist_id: phlebotomistId,
  });
  return data;
}

// ── Status / Priority helpers ──────────────────────────

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  confirmed: "bg-blue-100 text-blue-800",
  assigned: "bg-indigo-100 text-indigo-800",
  "in-progress": "bg-purple-100 text-purple-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
  "sample-collected": "bg-teal-100 text-teal-800",
  "report-ready": "bg-emerald-100 text-emerald-800",
};

const priorityColors: Record<string, string> = {
  normal: "bg-gray-100 text-gray-700",
  urgent: "bg-orange-100 text-orange-800",
  stat: "bg-red-100 text-red-800",
};

const ORDER_STATUSES = [
  "pending",
  "confirmed",
  "assigned",
  "in-progress",
  "sample-collected",
  "completed",
  "report-ready",
  "cancelled",
];

// ── Page Component ─────────────────────────────────────

export default function BookingsPage() {
  const queryClient = useQueryClient();

  // Filters
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterCity, setFilterCity] = useState("");
  const [filterClientId, setFilterClientId] = useState("");
  const [filterPhlebotomistId, setFilterPhlebotomistId] = useState("");
  const [filterPriority, setFilterPriority] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  // Bulk selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkAssignOpen, setBulkAssignOpen] = useState(false);
  const [bulkPhlebId, setBulkPhlebId] = useState("");

  // Single assign dialog
  const [assignOpen, setAssignOpen] = useState(false);
  const [assignBooking, setAssignBooking] = useState<Booking | null>(null);
  const [assignPhlebId, setAssignPhlebId] = useState("");

  // Queries
  const { data: bookingsData, isLoading } = useQuery({
    queryKey: [
      "bookings",
      page,
      search,
      filterStatus,
      filterCity,
      filterClientId,
      filterPhlebotomistId,
      filterPriority,
      dateFrom,
      dateTo,
    ],
    queryFn: () =>
      fetchBookings({
        page,
        search,
        status: filterStatus,
        client_id: filterClientId,
        phlebotomist_id: filterPhlebotomistId,
        city: filterCity,
        date_from: dateFrom,
        date_to: dateTo,
        priority: filterPriority,
      }),
    placeholderData: (prev) => prev,
  });

  const { data: phlebsData } = useQuery({
    queryKey: ["phlebotomists-active"],
    queryFn: fetchPhlebotomists,
  });

  const { data: clientsData } = useQuery({
    queryKey: ["clients-active"],
    queryFn: fetchClients,
  });

  const phlebotomists = phlebsData?.items ?? phlebsData?.data ?? [];
  const clients = clientsData?.items ?? [];
  const bookings = bookingsData?.items ?? [];

  // Mutations
  const assignMutation = useMutation({
    mutationFn: ({ orderId, phlebId }: { orderId: string; phlebId: string }) =>
      assignPhlebotomist(orderId, phlebId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      setAssignOpen(false);
      setAssignBooking(null);
      setAssignPhlebId("");
    },
  });

  const bulkAssignMutation = useMutation({
    mutationFn: ({ orderIds, phlebId }: { orderIds: string[]; phlebId: string }) =>
      bulkAssignPhlebotomist(orderIds, phlebId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      setBulkAssignOpen(false);
      setBulkPhlebId("");
      setSelectedIds(new Set());
    },
  });

  // Selection helpers
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === bookings.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(bookings.map((b) => b.id)));
    }
  };

  // Filter phlebotomists by zone for assignment
  const filteredPhlebsForAssign = useMemo(() => {
    if (!assignBooking?.zone) return phlebotomists;
    return phlebotomists.filter(
      (p) => p.zones?.some((z) => z.id === assignBooking.zone?.id) ?? false
    );
  }, [assignBooking, phlebotomists]);

  // ── Columns ──────────────────────────────────────────

  const columns: ColumnDef<Booking, unknown>[] = [
    {
      id: "select",
      header: () => (
        <input
          type="checkbox"
          checked={bookings.length > 0 && selectedIds.size === bookings.length}
          onChange={toggleSelectAll}
          className="rounded border-gray-300"
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={selectedIds.has(row.original.id)}
          onChange={() => toggleSelect(row.original.id)}
          className="rounded border-gray-300"
        />
      ),
    },
    {
      accessorKey: "booking_id",
      header: "Booking ID",
      cell: ({ row }) => (
        <Link
          href={`/bookings/${row.original.id}`}
          className="font-medium text-primary-600 hover:underline"
        >
          {row.original.booking_id}
        </Link>
      ),
    },
    {
      id: "patient",
      header: "Patient",
      cell: ({ row }) => (
        <div>
          <div className="text-sm font-medium">{row.original.patient?.name}</div>
          <div className="text-xs text-gray-500">{row.original.patient?.phone}</div>
        </div>
      ),
    },
    {
      id: "client",
      header: "Client",
      cell: ({ row }) => (
        <span className="text-sm">{row.original.client?.name ?? "—"}</span>
      ),
    },
    {
      id: "phlebotomist",
      header: "Phlebotomist",
      cell: ({ row }) =>
        row.original.phlebotomist ? (
          <span className="text-sm">{row.original.phlebotomist.name}</span>
        ) : (
          <span className="text-xs text-gray-400 italic">Unassigned</span>
        ),
    },
    {
      accessorKey: "scheduled_date",
      header: "Date",
      cell: ({ row }) => (
        <div className="text-sm">
          <div>{row.original.scheduled_date}</div>
          {row.original.scheduled_time && (
            <div className="text-xs text-gray-500">{row.original.scheduled_time}</div>
          )}
        </div>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge className={statusColors[row.original.status] ?? "bg-gray-100 text-gray-800"}>
          {row.original.status}
        </Badge>
      ),
    },
    {
      accessorKey: "priority",
      header: "Priority",
      cell: ({ row }) => (
        <Badge className={priorityColors[row.original.priority] ?? ""}>
          {row.original.priority}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="rounded p-1 hover:bg-gray-100">
              <MoreHorizontal className="h-4 w-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link href={`/bookings/${row.original.id}`}>
                <Eye className="mr-2 h-4 w-4" /> View Details
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                setAssignBooking(row.original);
                setAssignPhlebId(row.original.phlebotomist?.id ?? "");
                setAssignOpen(true);
              }}
            >
              <UserPlus className="mr-2 h-4 w-4" /> Assign Phlebotomist
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  // ── Render ───────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bookings</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage orders, assign phlebotomists, and track status.
          </p>
        </div>
        <div className="flex gap-2">
          {selectedIds.size > 0 && (
            <Button
              onClick={() => setBulkAssignOpen(true)}
              className="gap-2"
            >
              <CheckSquare className="h-4 w-4" />
              Assign ({selectedIds.size})
            </Button>
          )}
          <Button
            variant="outline"
            onClick={() => setShowFilters((v) => !v)}
            className="gap-2"
          >
            <Filter className="h-4 w-4" />
            Filters
          </Button>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              placeholder="Search by booking ID, patient name..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-md border border-gray-300 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => {
              setFilterStatus(e.target.value);
              setPage(1);
            }}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Statuses</option>
            {ORDER_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1).replace("-", " ")}
              </option>
            ))}
          </select>
          <select
            value={filterPriority}
            onChange={(e) => {
              setFilterPriority(e.target.value);
              setPage(1);
            }}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Priorities</option>
            <option value="normal">Normal</option>
            <option value="urgent">Urgent</option>
            <option value="stat">STAT</option>
          </select>
        </div>

        {showFilters && (
          <div className="flex flex-wrap gap-3 rounded-md border border-gray-200 bg-gray-50 p-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Date From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setPage(1);
                }}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Date To</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setPage(1);
                }}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Client</label>
              <select
                value={filterClientId}
                onChange={(e) => {
                  setFilterClientId(e.target.value);
                  setPage(1);
                }}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All Clients</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Phlebotomist</label>
              <select
                value={filterPhlebotomistId}
                onChange={(e) => {
                  setFilterPhlebotomistId(e.target.value);
                  setPage(1);
                }}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All Phlebotomists</option>
                {phlebotomists.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">City</label>
              <input
                placeholder="Filter by city"
                value={filterCity}
                onChange={(e) => {
                  setFilterCity(e.target.value);
                  setPage(1);
                }}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={() => {
                  setDateFrom("");
                  setDateTo("");
                  setFilterClientId("");
                  setFilterPhlebotomistId("");
                  setFilterCity("");
                  setFilterPriority("");
                  setFilterStatus("");
                  setSearch("");
                  setPage(1);
                }}
                className="rounded-md border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
              >
                Clear All
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : (
        <>
          <DataTable columns={columns} data={bookings} />
          {bookingsData && bookingsData.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Page {bookingsData.page} of {bookingsData.total_pages} ({bookingsData.total} total)
              </p>
              <div className="flex gap-2">
                <button
                  className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </button>
                <button
                  className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
                  disabled={page >= bookingsData.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Single Assign Dialog */}
      <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Phlebotomist</DialogTitle>
          </DialogHeader>
          {assignBooking && (
            <div className="space-y-4">
              <div className="rounded-md border bg-gray-50 p-3 text-sm">
                <p>
                  <span className="font-medium">Booking:</span> {assignBooking.booking_id}
                </p>
                <p>
                  <span className="font-medium">Patient:</span> {assignBooking.patient?.name}
                </p>
                {assignBooking.zone && (
                  <p>
                    <span className="font-medium">Zone:</span> {assignBooking.zone.name}
                  </p>
                )}
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Select Phlebotomist
                  {assignBooking.zone && (
                    <span className="ml-1 text-xs text-gray-400">
                      (filtered by zone: {assignBooking.zone.name})
                    </span>
                  )}
                </label>
                <select
                  value={assignPhlebId}
                  onChange={(e) => setAssignPhlebId(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Select...</option>
                  {filteredPhlebsForAssign.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} — {p.phone}
                    </option>
                  ))}
                </select>
                {filteredPhlebsForAssign.length === 0 && (
                  <p className="mt-1 text-xs text-amber-600">
                    No phlebotomists available for this zone. Showing all:
                  </p>
                )}
              </div>
              {filteredPhlebsForAssign.length === 0 && (
                <select
                  value={assignPhlebId}
                  onChange={(e) => setAssignPhlebId(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Select...</option>
                  {phlebotomists.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} — {p.phone}
                    </option>
                  ))}
                </select>
              )}
              {assignMutation.isError && (
                <p className="text-sm text-red-600">Assignment failed. Please try again.</p>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={!assignPhlebId || assignMutation.isPending}
              onClick={() => {
                if (assignBooking && assignPhlebId) {
                  assignMutation.mutate({
                    orderId: assignBooking.id,
                    phlebId: assignPhlebId,
                  });
                }
              }}
            >
              {assignMutation.isPending ? "Assigning..." : "Assign"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Assign Dialog */}
      <Dialog open={bulkAssignOpen} onOpenChange={setBulkAssignOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bulk Assign Phlebotomist</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Assign a phlebotomist to <strong>{selectedIds.size}</strong> selected order(s).
            </p>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Select Phlebotomist
              </label>
              <select
                value={bulkPhlebId}
                onChange={(e) => setBulkPhlebId(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Select...</option>
                {phlebotomists.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {p.phone}
                  </option>
                ))}
              </select>
            </div>
            {bulkAssignMutation.isError && (
              <p className="text-sm text-red-600">Bulk assignment failed. Please try again.</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkAssignOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={!bulkPhlebId || bulkAssignMutation.isPending}
              onClick={() => {
                if (bulkPhlebId) {
                  bulkAssignMutation.mutate({
                    orderIds: Array.from(selectedIds),
                    phlebId: bulkPhlebId,
                  });
                }
              }}
            >
              {bulkAssignMutation.isPending ? "Assigning..." : `Assign to ${selectedIds.size} Orders`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
