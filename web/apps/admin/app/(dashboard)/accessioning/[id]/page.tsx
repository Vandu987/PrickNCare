"use client";

import React from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  User,
  Calendar,
  Phone,
  Package,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Loader2,
  FlaskConical,
  Thermometer,
} from "lucide-react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// ── Types ──────────────────────────────────────────────

interface Patient {
  id: string;
  name: string;
  phone: string;
  email?: string;
  age?: number;
  gender?: string;
}

interface Test {
  id: string;
  name: string;
  sample_type?: string;
  code?: string;
}

interface Vial {
  type: string;
  quantity: number;
}

interface AccessioningRecord {
  id: string;
  order_id: string;
  booking_id: string;
  patient: Patient;
  tests: Test[];
  barcode?: string;
  status: string;
  priority: "normal" | "urgent" | "stat";
  scheduled_date: string;
  accessioned_at?: string;
  accessioned_by?: string;
  acceptance_status?: "accepted" | "hold" | "rejected";
  integrity?: string;
  temperature_ok?: boolean;
  vials?: Vial[];
  notes?: string;
}

// ── Helpers ────────────────────────────────────────────

const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  accepted: {
    color: "bg-green-100 text-green-800",
    icon: <CheckCircle2 className="h-4 w-4 text-green-600" />,
    label: "Accepted",
  },
  hold: {
    color: "bg-yellow-100 text-yellow-800",
    icon: <AlertTriangle className="h-4 w-4 text-yellow-600" />,
    label: "On Hold",
  },
  rejected: {
    color: "bg-red-100 text-red-800",
    icon: <XCircle className="h-4 w-4 text-red-600" />,
    label: "Rejected",
  },
};

const priorityColors: Record<string, string> = {
  normal: "bg-gray-100 text-gray-700",
  urgent: "bg-orange-100 text-orange-800",
  stat: "bg-red-100 text-red-800",
};

// ── API ────────────────────────────────────────────────

async function fetchAccessionDetail(id: string): Promise<AccessioningRecord> {
  const { data } = await api.get(`/accessioning/${id}`);
  return data.data ?? data;
}

// ── Page Component ─────────────────────────────────────

export default function AccessioningDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: record, isLoading, isError } = useQuery({
    queryKey: ["accessioning-detail", id],
    queryFn: () => fetchAccessionDetail(id),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (isError || !record) {
    return (
      <div className="space-y-4">
        <Button variant="outline" onClick={() => router.back()} className="gap-2">
          <ArrowLeft className="h-4 w-4" /> Back
        </Button>
        <div className="py-12 text-center text-sm text-gray-500">
          Could not load accessioning record.
        </div>
      </div>
    );
  }

  const acceptance = record.acceptance_status
    ? statusConfig[record.acceptance_status]
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" asChild>
            <Link href="/accessioning">
              <ArrowLeft className="mr-1 h-4 w-4" /> Back
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {record.booking_id}
            </h1>
            <p className="text-sm text-gray-500">Accessioning Detail</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={priorityColors[record.priority] ?? ""}>
            {record.priority}
          </Badge>
          {acceptance && (
            <Badge className={acceptance.color}>
              <span className="mr-1">{acceptance.icon}</span>
              {acceptance.label}
            </Badge>
          )}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Patient Info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <User className="h-4 w-4" /> Patient Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Name</span>
              <span className="font-medium">{record.patient?.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Phone</span>
              <span>{record.patient?.phone}</span>
            </div>
            {record.patient?.email && (
              <div className="flex justify-between">
                <span className="text-gray-500">Email</span>
                <span>{record.patient.email}</span>
              </div>
            )}
            {record.patient?.age && (
              <div className="flex justify-between">
                <span className="text-gray-500">Age / Gender</span>
                <span>
                  {record.patient.age} yrs{record.patient.gender ? ` / ${record.patient.gender}` : ""}
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Order Info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Calendar className="h-4 w-4" /> Order Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Order ID</span>
              <span className="font-medium">{record.order_id ?? record.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Booking ID</span>
              <span>{record.booking_id}</span>
            </div>
            {record.barcode && (
              <div className="flex justify-between">
                <span className="text-gray-500">Barcode</span>
                <span className="font-mono">{record.barcode}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-500">Scheduled Date</span>
              <span>{record.scheduled_date}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Status</span>
              <Badge variant="outline">{record.status}</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Tests */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <FlaskConical className="h-4 w-4" /> Tests
            </CardTitle>
          </CardHeader>
          <CardContent>
            {record.tests?.length ? (
              <div className="space-y-2">
                {record.tests.map((test) => (
                  <div
                    key={test.id}
                    className="flex items-center justify-between rounded border px-3 py-2 text-sm"
                  >
                    <div>
                      <span className="font-medium">{test.name}</span>
                      {test.code && (
                        <span className="ml-2 text-xs text-gray-400">{test.code}</span>
                      )}
                    </div>
                    {test.sample_type && (
                      <Badge variant="outline" className="text-xs">
                        {test.sample_type}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No tests listed.</p>
            )}
          </CardContent>
        </Card>

        {/* Accessioning Details */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Package className="h-4 w-4" /> Accessioning Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {record.accessioned_at ? (
              <>
                <div className="flex justify-between">
                  <span className="text-gray-500">Accessioned At</span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(record.accessioned_at).toLocaleString()}
                  </span>
                </div>
                {record.accessioned_by && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Accessioned By</span>
                    <span>{record.accessioned_by}</span>
                  </div>
                )}

                {/* Acceptance */}
                {acceptance && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Acceptance</span>
                    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${acceptance.color}`}>
                      {acceptance.icon} {acceptance.label}
                    </span>
                  </div>
                )}

                {/* Integrity */}
                {record.integrity && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Sample Integrity</span>
                    <span className="capitalize">{record.integrity}</span>
                  </div>
                )}

                {/* Temperature */}
                {record.temperature_ok !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Temperature</span>
                    <span className="flex items-center gap-1">
                      <Thermometer className="h-3 w-3" />
                      {record.temperature_ok ? (
                        <span className="text-green-600">OK</span>
                      ) : (
                        <span className="text-red-600">Out of range</span>
                      )}
                    </span>
                  </div>
                )}

                {/* Vials */}
                {record.vials && record.vials.length > 0 && (
                  <div>
                    <p className="mb-1 font-medium text-gray-700">Vials</p>
                    <div className="space-y-1">
                      {record.vials.map((v, i) => (
                        <div
                          key={i}
                          className="flex justify-between rounded bg-gray-50 px-2 py-1 text-xs"
                        >
                          <span>{v.type}</span>
                          <span className="font-medium">×{v.quantity}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Notes */}
                {record.notes && (
                  <div>
                    <p className="font-medium text-gray-700">Notes</p>
                    <p className="mt-1 rounded bg-gray-50 p-2 text-gray-600">
                      {record.notes}
                    </p>
                  </div>
                )}
              </>
            ) : (
              <div className="py-4 text-center text-gray-500">
                <Package className="mx-auto mb-2 h-8 w-8 text-gray-300" />
                <p>Not yet accessioned</p>
                <Button size="sm" className="mt-3" asChild>
                  <Link href="/accessioning">Go to Accessioning</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
