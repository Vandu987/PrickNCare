"use client";

import React, { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  UserPlus,
  Clock,
  MapPin,
  Phone,
  Mail,
  Package,
  IndianRupee,
  Calendar,
  User,
  Building2,
  CheckCircle2,
} from "lucide-react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// ── Types ──────────────────────────────────────────────

interface Patient {
  id: string;
  name: string;
  phone: string;
  email?: string;
  age?: number;
  gender?: string;
  address?: string;
}

interface Client {
  id: string;
  name: string;
  contact_person?: string;
  contact_phone?: string;
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

interface TestPackage {
  id: string;
  name: string;
  price: number;
  tests?: string[];
}

interface StatusHistoryEntry {
  status: string;
  changed_at: string;
  changed_by?: string;
  notes?: string;
}

interface BookingDetail {
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
  address: string;
  zone: Zone | null;
  packages: TestPackage[];
  total_amount: number;
  discount: number;
  net_amount: number;
  notes?: string;
  status_history: StatusHistoryEntry[];
  created_at: string;
  updated_at: string;
}

interface PhlebotomistOption {
  id: string;
  name: string;
  phone: string;
  zones: { id: string; name: string }[];
}

// ── API ────────────────────────────────────────────────

async function fetchBooking(id: string): Promise<BookingDetail> {
  const { data } = await api.get(`/orders/${id}`);
  return data.data ?? data;
}

async function fetchPhlebotomists(): Promise<{ data: PhlebotomistOption[] }> {
  const { data } = await api.get("/phlebotomists?status=active");
  return data;
}

async function assignPhlebotomist(orderId: string, phlebotomistId: string) {
  const { data } = await api.post(`/orders/${orderId}/assign`, {
    phlebotomist_id: phlebotomistId,
  });
  return data;
}

async function updateOrderStatus(orderId: string, status: string, notes?: string) {
  const { data } = await api.put(`/orders/${orderId}/status`, { status, notes });
  return data;
}

// ── Status helpers ─────────────────────────────────────

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  assigned: "bg-indigo-100 text-indigo-800",
  accepted: "bg-blue-100 text-blue-800",
  in_transit: "bg-purple-100 text-purple-800",
  collected: "bg-teal-100 text-teal-800",
  uncollected: "bg-orange-100 text-orange-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
  nsa: "bg-gray-100 text-gray-800",
  sample_rejected: "bg-red-100 text-red-800",
  sample_hold: "bg-amber-100 text-amber-800",
};

const priorityColors: Record<string, string> = {
  normal: "bg-gray-100 text-gray-700",
  high: "bg-orange-100 text-orange-800",
};

const STATUS_TRANSITIONS: Record<string, string[]> = {
  pending: ["assigned", "cancelled", "nsa"],
  assigned: ["accepted", "cancelled"],
  accepted: ["in_transit", "cancelled"],
  in_transit: ["collected", "uncollected"],
  collected: ["completed", "sample_rejected", "sample_hold"],
  uncollected: ["pending"],
  completed: [],
  cancelled: [],
  nsa: [],
  sample_rejected: [],
  sample_hold: ["completed"],
};

const STATUS_ORDER = [
  "pending",
  "assigned",
  "accepted",
  "in_transit",
  "collected",
  "completed",
];

// ── Page Component ─────────────────────────────────────

export default function BookingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const bookingId = params.id as string;

  const [assignOpen, setAssignOpen] = useState(false);
  const [assignPhlebId, setAssignPhlebId] = useState("");
  const [statusNotes, setStatusNotes] = useState("");

  const { data: booking, isLoading } = useQuery({
    queryKey: ["booking", bookingId],
    queryFn: () => fetchBooking(bookingId),
    enabled: !!bookingId,
  });

  const { data: phlebsData } = useQuery({
    queryKey: ["phlebotomists-active"],
    queryFn: fetchPhlebotomists,
  });

  const phlebotomists = phlebsData?.data ?? [];

  const filteredPhlebs = useMemo(() => {
    if (!booking?.zone) return phlebotomists;
    const zoneFiltered = phlebotomists.filter(
      (p) => p.zones?.some((z) => z.id === booking.zone?.id) ?? false
    );
    return zoneFiltered.length > 0 ? zoneFiltered : phlebotomists;
  }, [booking, phlebotomists]);

  const assignMutation = useMutation({
    mutationFn: ({ orderId, phlebId }: { orderId: string; phlebId: string }) =>
      assignPhlebotomist(orderId, phlebId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["booking", bookingId] });
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      setAssignOpen(false);
      setAssignPhlebId("");
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ status, notes }: { status: string; notes?: string }) =>
      updateOrderStatus(bookingId, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["booking", bookingId] });
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      setStatusNotes("");
    },
  });

  const validTransitions = booking ? STATUS_TRANSITIONS[booking.status] ?? [] : [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="py-24 text-center">
        <p className="text-gray-500">Booking not found.</p>
        <Link href="/bookings" className="mt-4 text-primary-600 hover:underline">
          Back to Bookings
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/bookings")}
            className="rounded-md p-1 hover:bg-gray-100"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-gray-900">{booking.booking_id}</h1>
              <Badge className={statusColors[booking.status] ?? "bg-gray-100 text-gray-800"}>
                {booking.status}
              </Badge>
              <Badge className={priorityColors[booking.priority] ?? ""}>
                {booking.priority}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Created {new Date(booking.created_at).toLocaleDateString("en-IN")}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => {
              setAssignPhlebId(booking.phlebotomist?.id ?? "");
              setAssignOpen(true);
            }}
            className="gap-2"
          >
            <UserPlus className="h-4 w-4" />
            {booking.phlebotomist ? "Reassign" : "Assign"} Phlebotomist
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main content - 2 cols */}
        <div className="space-y-6 lg:col-span-2">
          {/* Patient Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <User className="h-4 w-4" /> Patient Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">{booking.patient?.name}</p>
                  {booking.patient?.age && booking.patient?.gender && (
                    <p className="text-sm text-gray-500">
                      {booking.patient.age} yrs, {booking.patient.gender}
                    </p>
                  )}
                </div>
                <div className="space-y-1">
                  {booking.patient?.phone && (
                    <p className="flex items-center gap-2 text-sm text-gray-600">
                      <Phone className="h-3.5 w-3.5" /> {booking.patient.phone}
                    </p>
                  )}
                  {booking.patient?.email && (
                    <p className="flex items-center gap-2 text-sm text-gray-600">
                      <Mail className="h-3.5 w-3.5" /> {booking.patient.email}
                    </p>
                  )}
                </div>
              </div>
              {booking.address && (
                <div className="mt-3 flex items-start gap-2 border-t pt-3">
                  <MapPin className="mt-0.5 h-3.5 w-3.5 text-gray-400" />
                  <p className="text-sm text-gray-600">{booking.address}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Schedule & Client */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Calendar className="h-4 w-4" /> Schedule
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm">
                  <span className="font-medium">Date:</span> {booking.scheduled_date}
                </p>
                {booking.scheduled_time && (
                  <p className="text-sm">
                    <span className="font-medium">Time:</span> {booking.scheduled_time}
                  </p>
                )}
                <p className="text-sm">
                  <span className="font-medium">City:</span> {booking.city}
                </p>
                {booking.zone && (
                  <p className="text-sm">
                    <span className="font-medium">Zone:</span> {booking.zone.name}
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Building2 className="h-4 w-4" /> Client
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm font-medium">{booking.client?.name ?? "—"}</p>
                {booking.client?.contact_person && (
                  <p className="text-sm text-gray-500">{booking.client.contact_person}</p>
                )}
                {booking.client?.contact_phone && (
                  <p className="flex items-center gap-2 text-sm text-gray-500">
                    <Phone className="h-3.5 w-3.5" /> {booking.client.contact_phone}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Packages & Pricing */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Package className="h-4 w-4" /> Packages & Pricing
              </CardTitle>
            </CardHeader>
            <CardContent>
              {booking.packages?.length > 0 ? (
                <div className="space-y-3">
                  <div className="divide-y rounded-md border">
                    {booking.packages.map((pkg) => (
                      <div key={pkg.id} className="flex items-center justify-between p-3">
                        <div>
                          <p className="text-sm font-medium">{pkg.name}</p>
                          {pkg.tests && pkg.tests.length > 0 && (
                            <p className="text-xs text-gray-500">
                              {pkg.tests.join(", ")}
                            </p>
                          )}
                        </div>
                        <p className="text-sm font-medium">₹{pkg.price}</p>
                      </div>
                    ))}
                  </div>
                  <div className="border-t pt-3 space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>Subtotal</span>
                      <span>₹{booking.total_amount}</span>
                    </div>
                    {booking.discount > 0 && (
                      <div className="flex justify-between text-sm text-green-600">
                        <span>Discount</span>
                        <span>-₹{booking.discount}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-sm font-semibold">
                      <span>Net Amount</span>
                      <span>₹{booking.net_amount}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-400">No packages listed.</p>
              )}
            </CardContent>
          </Card>

          {/* Notes */}
          {booking.notes && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600 whitespace-pre-wrap">{booking.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar - 1 col */}
        <div className="space-y-6">
          {/* Assignment Panel */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <UserPlus className="h-4 w-4" /> Assignment
              </CardTitle>
            </CardHeader>
            <CardContent>
              {booking.phlebotomist ? (
                <div className="space-y-2">
                  <div className="rounded-md border bg-green-50 p-3">
                    <p className="text-sm font-medium text-green-900">
                      {booking.phlebotomist.name}
                    </p>
                    <p className="flex items-center gap-1 text-xs text-green-700">
                      <Phone className="h-3 w-3" /> {booking.phlebotomist.phone}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => {
                      setAssignPhlebId(booking.phlebotomist?.id ?? "");
                      setAssignOpen(true);
                    }}
                  >
                    Reassign
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-gray-400 italic">No phlebotomist assigned</p>
                  <Button
                    size="sm"
                    className="w-full gap-2"
                    onClick={() => {
                      setAssignPhlebId("");
                      setAssignOpen(true);
                    }}
                  >
                    <UserPlus className="h-4 w-4" /> Assign Now
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Status Actions */}
          {validTransitions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Update Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <textarea
                  placeholder="Notes (optional)"
                  value={statusNotes}
                  onChange={(e) => setStatusNotes(e.target.value)}
                  rows={2}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <div className="flex flex-wrap gap-2">
                  {validTransitions.map((status) => (
                    <Button
                      key={status}
                      variant={status === "cancelled" ? "destructive" : "outline"}
                      size="sm"
                      disabled={statusMutation.isPending}
                      onClick={() =>
                        statusMutation.mutate({
                          status,
                          notes: statusNotes || undefined,
                        })
                      }
                    >
                      {status.charAt(0).toUpperCase() + status.slice(1).replace("-", " ")}
                    </Button>
                  ))}
                </div>
                {statusMutation.isError && (
                  <p className="text-xs text-red-600">Failed to update status.</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Status Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock className="h-4 w-4" /> Status Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              {booking.status_history?.length > 0 ? (
                <div className="relative space-y-0">
                  {booking.status_history.map((entry, i) => {
                    const isLast = i === booking.status_history.length - 1;
                    return (
                      <div key={i} className="relative flex gap-3 pb-4">
                        {/* Line */}
                        {!isLast && (
                          <div className="absolute left-[9px] top-5 h-full w-px bg-gray-200" />
                        )}
                        {/* Dot */}
                        <div
                          className={`relative mt-1 h-[18px] w-[18px] flex-shrink-0 rounded-full border-2 ${
                            isLast
                              ? "border-primary-600 bg-primary-100"
                              : "border-gray-300 bg-white"
                          }`}
                        >
                          {isLast && (
                            <CheckCircle2 className="h-3 w-3 absolute top-[1px] left-[1px] text-primary-600" />
                          )}
                        </div>
                        {/* Content */}
                        <div className="min-w-0">
                          <Badge
                            className={`${statusColors[entry.status] ?? "bg-gray-100 text-gray-800"} text-[10px]`}
                          >
                            {entry.status}
                          </Badge>
                          <p className="mt-0.5 text-xs text-gray-500">
                            {new Date(entry.changed_at).toLocaleString("en-IN")}
                          </p>
                          {entry.changed_by && (
                            <p className="text-xs text-gray-400">by {entry.changed_by}</p>
                          )}
                          {entry.notes && (
                            <p className="mt-0.5 text-xs text-gray-600">{entry.notes}</p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="space-y-2">
                  {STATUS_ORDER.map((s) => {
                    const currentIdx = STATUS_ORDER.indexOf(booking.status);
                    const sIdx = STATUS_ORDER.indexOf(s);
                    const isPast = sIdx <= currentIdx;
                    return (
                      <div key={s} className="flex items-center gap-2">
                        <div
                          className={`h-2.5 w-2.5 rounded-full ${
                            isPast ? "bg-primary-600" : "bg-gray-200"
                          }`}
                        />
                        <span
                          className={`text-xs ${
                            isPast ? "font-medium text-gray-900" : "text-gray-400"
                          }`}
                        >
                          {s.charAt(0).toUpperCase() + s.slice(1).replace("-", " ")}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Assign Dialog */}
      <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {booking.phlebotomist ? "Reassign" : "Assign"} Phlebotomist
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="rounded-md border bg-gray-50 p-3 text-sm">
              <p>
                <span className="font-medium">Booking:</span> {booking.booking_id}
              </p>
              <p>
                <span className="font-medium">Patient:</span> {booking.patient?.name}
              </p>
              {booking.zone && (
                <p>
                  <span className="font-medium">Zone:</span> {booking.zone.name}
                </p>
              )}
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Select Phlebotomist
                {booking.zone && (
                  <span className="ml-1 text-xs text-gray-400">
                    (showing zone: {booking.zone.name})
                  </span>
                )}
              </label>
              <select
                value={assignPhlebId}
                onChange={(e) => setAssignPhlebId(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Select...</option>
                {filteredPhlebs.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {p.phone}
                    {p.zones?.length ? ` (${p.zones.map((z) => z.name).join(", ")})` : ""}
                  </option>
                ))}
              </select>
            </div>
            {assignMutation.isError && (
              <p className="text-sm text-red-600">Assignment failed. Please try again.</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={!assignPhlebId || assignMutation.isPending}
              onClick={() => {
                if (assignPhlebId) {
                  assignMutation.mutate({ orderId: bookingId, phlebId: assignPhlebId });
                }
              }}
            >
              {assignMutation.isPending ? "Assigning..." : "Assign"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
