"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Order, OrderStatus } from "@/types";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ArrowLeft,
  Loader2,
  User,
  Phone,
  MapPin,
  Calendar,
  Clock,
  IndianRupee,
  FlaskConical,
  XCircle,
  CheckCircle2,
  Circle,
  AlertCircle,
} from "lucide-react";
import { useState } from "react";

// ── Types ──

interface OrderHistoryEntry {
  id: number;
  status: OrderStatus;
  note?: string;
  created_at: string;
  created_by?: string;
}

// ── Constants ──

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  confirmed: "bg-blue-100 text-blue-800",
  assigned: "bg-purple-100 text-purple-800",
  in_progress: "bg-indigo-100 text-indigo-800",
  sample_collected: "bg-cyan-100 text-cyan-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

const priorityColors: Record<string, string> = {
  normal: "bg-gray-100 text-gray-700",
  high: "bg-orange-100 text-orange-700",
};

const STATUS_STEPS: OrderStatus[] = [
  "pending",
  "confirmed",
  "assigned",
  "in_progress",
  "sample_collected",
  "completed",
];

function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatDateTime(date: string): string {
  return new Date(date).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Timeline Component ──

function StatusTimeline({ history }: { history: OrderHistoryEntry[] }) {
  const completedStatuses = new Set(history.map((h) => h.status));
  const isCancelled = completedStatuses.has("cancelled");

  return (
    <div className="space-y-0">
      {/* Step indicators */}
      <div className="hidden sm:flex items-center justify-between mb-8">
        {STATUS_STEPS.map((step, idx) => {
          const done = completedStatuses.has(step);
          const isCurrent =
            !isCancelled &&
            done &&
            (idx === STATUS_STEPS.length - 1 ||
              !completedStatuses.has(STATUS_STEPS[idx + 1]));

          return (
            <div key={step} className="flex items-center flex-1 last:flex-initial">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 ${
                    done
                      ? isCurrent
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-green-500 bg-green-500 text-white"
                      : "border-muted-foreground/30 bg-background text-muted-foreground/50"
                  }`}
                >
                  {done ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <Circle className="h-4 w-4" />
                  )}
                </div>
                <span
                  className={`mt-1.5 text-xs text-center max-w-[80px] ${
                    done ? "font-medium text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {formatStatus(step)}
                </span>
              </div>
              {idx < STATUS_STEPS.length - 1 && (
                <div
                  className={`mx-1 h-0.5 flex-1 ${
                    completedStatuses.has(STATUS_STEPS[idx + 1])
                      ? "bg-green-500"
                      : "bg-muted-foreground/20"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {isCancelled && (
        <div className="mb-4 flex items-center gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          <XCircle className="h-4 w-4" />
          This order has been cancelled.
        </div>
      )}

      {/* Detailed history */}
      <div className="space-y-0">
        {history.map((entry, idx) => (
          <div key={entry.id} className="flex gap-3">
            {/* Vertical line + dot */}
            <div className="flex flex-col items-center">
              <div
                className={`mt-1 h-3 w-3 rounded-full ${
                  entry.status === "cancelled"
                    ? "bg-red-500"
                    : idx === 0
                      ? "bg-primary"
                      : "bg-green-500"
                }`}
              />
              {idx < history.length - 1 && (
                <div className="w-px flex-1 bg-muted-foreground/20" />
              )}
            </div>
            {/* Content */}
            <div className="pb-6">
              <p className="text-sm font-medium leading-none">
                {formatStatus(entry.status)}
              </p>
              {entry.note && (
                <p className="mt-1 text-sm text-muted-foreground">{entry.note}</p>
              )}
              <p className="mt-1 text-xs text-muted-foreground">
                {formatDateTime(entry.created_at)}
                {entry.created_by && ` · by ${entry.created_by}`}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ──

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showCancelDialog, setShowCancelDialog] = useState(false);

  const orderId = params.id;

  // ── Fetch Order ──
  const {
    data: order,
    isLoading,
    error,
  } = useQuery<Order>({
    queryKey: ["order", orderId],
    queryFn: async () => {
      const { data } = await api.get(`/orders/${orderId}/`);
      return data;
    },
  });

  // ── Fetch History ──
  const { data: history = [] } = useQuery<OrderHistoryEntry[]>({
    queryKey: ["order-history", orderId],
    queryFn: async () => {
      const { data } = await api.get(`/orders/${orderId}/history/`);
      return data;
    },
    enabled: !!order,
  });

  // ── Cancel Mutation ──
  const cancelMutation = useMutation({
    mutationFn: async () => {
      await api.patch(`/orders/${orderId}/`, { status: "cancelled" });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["order", orderId] });
      queryClient.invalidateQueries({ queryKey: ["order-history", orderId] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      setShowCancelDialog(false);
    },
  });

  const isCancellable =
    order &&
    order.status !== "cancelled" &&
    order.status !== "completed" &&
    order.status !== "sample_collected";

  // ── Loading / Error ──
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <AlertCircle className="mb-3 h-10 w-10 text-destructive" />
        <p className="text-lg font-medium">Order not found</p>
        <p className="mt-1 text-sm text-muted-foreground">
          The order may have been deleted or you don&apos;t have access.
        </p>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/orders")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Orders
        </Button>
      </div>
    );
  }

  const totalPackages = order.patients.reduce(
    (sum, p) => sum + p.packages.length,
    0
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/orders")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-2xl font-bold tracking-tight">
                {order.order_number}
              </h1>
              <Badge variant="secondary" className={statusColors[order.status] ?? ""}>
                {formatStatus(order.status)}
              </Badge>
              <Badge variant="secondary" className={priorityColors[order.priority] ?? ""}>
                {order.priority === "high" ? "⚡ High" : "Normal"}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Placed on {formatDate(order.created_at)}
            </p>
          </div>
        </div>
        {isCancellable && (
          <Button
            variant="destructive"
            onClick={() => setShowCancelDialog(true)}
          >
            <XCircle className="mr-2 h-4 w-4" />
            Cancel Order
          </Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column - 2/3 */}
        <div className="space-y-6 lg:col-span-2">
          {/* Schedule & Address */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Collection Details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <div className="flex items-start gap-2">
                <Calendar className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Scheduled Date</p>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(order.scheduled_date)}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <Clock className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Time Slot</p>
                  <p className="text-sm text-muted-foreground">
                    {order.scheduled_time_slot}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2 sm:col-span-2">
                <MapPin className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Collection Address</p>
                  <p className="text-sm text-muted-foreground">
                    {order.collection_address}, {order.city} – {order.pincode}
                  </p>
                </div>
              </div>
              {order.notes && (
                <div className="sm:col-span-2">
                  <p className="text-sm font-medium">Notes</p>
                  <p className="text-sm text-muted-foreground">{order.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Patients & Packages */}
          {order.patients.map((patient, idx) => (
            <Card key={patient.id}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <User className="h-4 w-4" />
                  Patient {order.patients.length > 1 ? idx + 1 : ""}: {patient.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Patient Info */}
                <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
                  <span>
                    <span className="text-muted-foreground">Age:</span>{" "}
                    {patient.age} yrs
                  </span>
                  <span>
                    <span className="text-muted-foreground">Gender:</span>{" "}
                    {patient.gender === "M"
                      ? "Male"
                      : patient.gender === "F"
                        ? "Female"
                        : "Other"}
                  </span>
                  <span className="flex items-center gap-1">
                    <Phone className="h-3.5 w-3.5 text-muted-foreground" />
                    {patient.phone}
                  </span>
                </div>

                {/* Packages */}
                <div>
                  <p className="mb-2 text-sm font-medium">Packages</p>
                  <div className="space-y-2">
                    {patient.packages.map((pkg) => (
                      <div
                        key={pkg.id}
                        className="flex items-center justify-between rounded-md border px-3 py-2"
                      >
                        <div className="flex items-center gap-2">
                          <FlaskConical className="h-4 w-4 text-muted-foreground" />
                          <div>
                            <p className="text-sm font-medium">{pkg.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {pkg.sample_type} · {pkg.tube_type}
                            </p>
                          </div>
                        </div>
                        <span className="flex items-center text-sm font-medium">
                          <IndianRupee className="h-3.5 w-3.5" />
                          {pkg.price.toLocaleString("en-IN")}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Status Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Order Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {history.length > 0 ? (
                <StatusTimeline history={history} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  No history available yet.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right column - 1/3 */}
        <div className="space-y-6">
          {/* Pricing */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Pricing Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {order.patients.map((patient) =>
                patient.packages.map((pkg) => (
                  <div
                    key={`${patient.id}-${pkg.id}`}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-muted-foreground truncate mr-2">
                      {pkg.name}
                      {order.patients.length > 1 && (
                        <span className="text-xs"> ({patient.name})</span>
                      )}
                    </span>
                    <span className="flex items-center whitespace-nowrap">
                      <IndianRupee className="h-3 w-3" />
                      {pkg.price.toLocaleString("en-IN")}
                    </span>
                  </div>
                ))
              )}
              <div className="border-t pt-3">
                <div className="flex items-center justify-between font-semibold">
                  <span>Total ({totalPackages} package{totalPackages !== 1 ? "s" : ""})</span>
                  <span className="flex items-center">
                    <IndianRupee className="h-3.5 w-3.5" />
                    {order.total_amount.toLocaleString("en-IN")}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Phlebotomist */}
          {order.assigned_phlebotomist && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Assigned Phlebotomist</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold">
                    {order.assigned_phlebotomist.full_name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")
                      .toUpperCase()
                      .slice(0, 2)}
                  </div>
                  <div>
                    <p className="text-sm font-medium">
                      {order.assigned_phlebotomist.full_name}
                    </p>
                    <p className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Phone className="h-3 w-3" />
                      {order.assigned_phlebotomist.phone}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Client Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Client</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p className="font-medium">{order.client.company_name}</p>
              <p className="text-muted-foreground">
                {order.client.contact_person}
              </p>
              <p className="flex items-center gap-1 text-muted-foreground">
                <Phone className="h-3 w-3" />
                {order.client.contact_phone}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Cancel Dialog */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Order</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel order{" "}
              <span className="font-semibold">{order.order_number}</span>? This
              action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCancelDialog(false)}
              disabled={cancelMutation.isPending}
            >
              Keep Order
            </Button>
            <Button
              variant="destructive"
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Cancel Order
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
