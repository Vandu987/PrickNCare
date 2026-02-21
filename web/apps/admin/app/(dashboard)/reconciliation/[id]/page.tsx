"use client";

import React from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle,
  Clock,
  AlertTriangle,
  DollarSign,
} from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// ── Types ──────────────────────────────────────────────

interface DiscrepancyResponse {
  id: string;
  type: string;
  amount: number;
  notes: string | null;
}

interface ReconciliationDetail {
  id: string;
  phlebotomist_id: string;
  date: string;
  expected_cash: number;
  cash_handed_over: number;
  submitted_cash: number | null;
  submitted_notes: string | null;
  net_discrepancy: number;
  status: string;
  created_by: string;
  verified_by: string | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
  discrepancies: DiscrepancyResponse[];
}

const STATUS_CONFIG: Record<string, { label: string; variant: string; icon: React.ReactNode }> = {
  draft: {
    label: "Draft",
    variant: "bg-gray-100 text-gray-800",
    icon: <Clock className="h-4 w-4" />,
  },
  pending_review: {
    label: "Pending Review",
    variant: "bg-yellow-100 text-yellow-800",
    icon: <AlertTriangle className="h-4 w-4" />,
  },
  confirmed: {
    label: "Confirmed",
    variant: "bg-green-100 text-green-800",
    icon: <CheckCircle className="h-4 w-4" />,
  },
  disputed: {
    label: "Disputed",
    variant: "bg-red-100 text-red-800",
    icon: <AlertTriangle className="h-4 w-4" />,
  },
};

const DISCREPANCY_LABELS: Record<string, string> = {
  fuel_allowance: "Fuel Allowance",
  cash_shortage: "Cash Shortage",
  overage: "Overage",
  patient_refund: "Patient Refund",
  incentive_adjustment: "Incentive Adjustment",
  other: "Other",
};

function formatCurrency(amount: number) {
  return `₹${amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// ── Component ──────────────────────────────────────────

export default function ReconciliationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const reconciliationId = params.id as string;

  const { data, isLoading, error } = useQuery({
    queryKey: ["reconciliation", reconciliationId],
    queryFn: async (): Promise<ReconciliationDetail> => {
      const { data } = await api.get(`/reconciliation/${reconciliationId}`);
      return data;
    },
  });

  const verifyMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/reconciliation/${reconciliationId}/verify`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reconciliation", reconciliationId] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground">
        Loading reconciliation details...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertTriangle className="mb-2 h-8 w-8 text-red-500" />
        <p className="text-muted-foreground">Failed to load reconciliation</p>
        <Button variant="outline" className="mt-4" onClick={() => router.back()}>
          Go Back
        </Button>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[data.status] ?? STATUS_CONFIG.draft;
  const canVerify = !data.verified_at && data.status !== "confirmed";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Reconciliation Details
            </h1>
            <p className="text-sm text-muted-foreground">
              {data.date} · ID: {data.id.slice(0, 8)}...
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${statusConfig.variant}`}
          >
            {statusConfig.icon}
            {statusConfig.label}
          </span>
          {canVerify && (
            <Button
              onClick={() => verifyMutation.mutate()}
              disabled={verifyMutation.isPending}
            >
              <CheckCircle className="mr-1 h-4 w-4" />
              {verifyMutation.isPending ? "Verifying..." : "Verify"}
            </Button>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Expected Cash
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(data.expected_cash)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Cash Handed Over
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(data.cash_handed_over)}
            </div>
          </CardContent>
        </Card>
        {data.submitted_cash !== null && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Submitted Cash
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(data.submitted_cash)}
              </div>
              {data.submitted_notes && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {data.submitted_notes}
                </p>
              )}
            </CardContent>
          </Card>
        )}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Net Discrepancy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={`text-2xl font-bold ${
                data.net_discrepancy === 0
                  ? "text-green-600"
                  : data.net_discrepancy > 0
                    ? "text-red-600"
                    : "text-blue-600"
              }`}
            >
              {formatCurrency(Math.abs(data.net_discrepancy))}
              {data.net_discrepancy > 0
                ? " Short"
                : data.net_discrepancy < 0
                  ? " Over"
                  : ""}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Discrepancies */}
      <Card>
        <CardHeader>
          <CardTitle>Discrepancies</CardTitle>
          <CardDescription>
            {data.discrepancies.length
              ? `${data.discrepancies.length} discrepancy item(s) recorded`
              : "No discrepancies recorded"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.discrepancies.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.discrepancies.map((disc) => (
                  <TableRow key={disc.id}>
                    <TableCell>
                      <Badge variant="outline">
                        {DISCREPANCY_LABELS[disc.type] ?? disc.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(disc.amount)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {disc.notes || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No discrepancies
            </p>
          )}
        </CardContent>
      </Card>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Info</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-y-2 text-sm md:grid-cols-4">
            <div>
              <p className="text-muted-foreground">Created</p>
              <p className="font-medium">{formatDateTime(data.created_at)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Updated</p>
              <p className="font-medium">{formatDateTime(data.updated_at)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Verified</p>
              <p className="font-medium">
                {data.verified_at ? formatDateTime(data.verified_at) : "Not yet"}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Status</p>
              <p className="font-medium capitalize">
                {data.status.replace(/_/g, " ")}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
