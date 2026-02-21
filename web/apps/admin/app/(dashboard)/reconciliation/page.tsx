"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Calendar,
  DollarSign,
  Plus,
  CheckCircle,
  AlertTriangle,
  Eye,
  X,
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// ── Types ──────────────────────────────────────────────

interface PhlebotomistSummary {
  phlebotomist_id: string;
  user_id: string;
  name: string;
  total_appointments: number;
  cash_collected: number;
  online_collected: number;
  total_collected: number;
}

interface PendingReconciliationResponse {
  date: string;
  items: PhlebotomistSummary[];
}

interface DiscrepancyItem {
  type: string;
  amount: number;
  notes: string;
}

interface DiscrepancyResponse {
  id: string;
  type: string;
  amount: number;
  notes: string | null;
}

interface ReconciliationResponse {
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

const DISCREPANCY_TYPES = [
  { value: "fuel_allowance", label: "Fuel Allowance" },
  { value: "cash_shortage", label: "Cash Shortage" },
  { value: "overage", label: "Overage" },
  { value: "patient_refund", label: "Patient Refund" },
  { value: "incentive_adjustment", label: "Incentive Adjustment" },
  { value: "other", label: "Other" },
];

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-800",
  pending_review: "bg-yellow-100 text-yellow-800",
  confirmed: "bg-green-100 text-green-800",
  disputed: "bg-red-100 text-red-800",
};

function formatCurrency(amount: number) {
  return `₹${amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function todayISO() {
  return new Date().toISOString().split("T")[0];
}

// ── API helpers ────────────────────────────────────────

async function fetchPending(date: string): Promise<PendingReconciliationResponse> {
  const { data } = await api.get("/reconciliation/pending", { params: { date } });
  return data;
}

async function fetchReconciliations(params: {
  date_from: string;
  date_to: string;
}): Promise<ReconciliationResponse[]> {
  // Use report endpoint to list; or fetch pending verifications
  // Since there's no list endpoint, we'll use report + individual gets
  // Actually let's just query pending that have status pending_review
  const { data } = await api.get("/reconciliation/report", { params });
  return data;
}

async function createReconciliation(body: {
  phlebotomist_id: string;
  date: string;
  cash_handed_over: number;
  discrepancies: DiscrepancyItem[];
}): Promise<ReconciliationResponse> {
  const { data } = await api.post("/reconciliation", body);
  return data;
}

async function verifyReconciliation(id: string): Promise<ReconciliationResponse> {
  const { data } = await api.post(`/reconciliation/${id}/verify`);
  return data;
}

// ── Component ──────────────────────────────────────────

export default function ReconciliationPage() {
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState(todayISO());
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedPhlebotomist, setSelectedPhlebotomist] = useState<PhlebotomistSummary | null>(null);
  const [cashHandedOver, setCashHandedOver] = useState("");
  const [discrepancies, setDiscrepancies] = useState<DiscrepancyItem[]>([]);
  const [activeTab, setActiveTab] = useState("pending");

  // Fetch pending reconciliations
  const { data: pendingData, isLoading: pendingLoading } = useQuery({
    queryKey: ["reconciliation-pending", selectedDate],
    queryFn: () => fetchPending(selectedDate),
  });

  // Fetch report for verification tab (pending_review items)
  const { data: reportData } = useQuery({
    queryKey: ["reconciliation-report", selectedDate],
    queryFn: () =>
      api
        .get("/reconciliation/report", {
          params: { date_from: selectedDate, date_to: selectedDate },
        })
        .then((r) => r.data),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: createReconciliation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reconciliation-pending"] });
      queryClient.invalidateQueries({ queryKey: ["reconciliation-report"] });
      setShowCreateDialog(false);
      resetForm();
    },
  });

  // Verify mutation
  const verifyMutation = useMutation({
    mutationFn: verifyReconciliation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reconciliation-pending"] });
      queryClient.invalidateQueries({ queryKey: ["reconciliation-report"] });
    },
  });

  function resetForm() {
    setSelectedPhlebotomist(null);
    setCashHandedOver("");
    setDiscrepancies([]);
  }

  function openCreateDialog(phleb: PhlebotomistSummary) {
    setSelectedPhlebotomist(phleb);
    setCashHandedOver("");
    setDiscrepancies([]);
    setShowCreateDialog(true);
  }

  function addDiscrepancy() {
    setDiscrepancies((prev) => [
      ...prev,
      { type: "cash_shortage", amount: 0, notes: "" },
    ]);
  }

  function updateDiscrepancy(index: number, field: keyof DiscrepancyItem, value: string | number) {
    setDiscrepancies((prev) =>
      prev.map((d, i) => (i === index ? { ...d, [field]: value } : d))
    );
  }

  function removeDiscrepancy(index: number) {
    setDiscrepancies((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSubmit() {
    if (!selectedPhlebotomist) return;
    createMutation.mutate({
      phlebotomist_id: selectedPhlebotomist.phlebotomist_id,
      date: selectedDate,
      cash_handed_over: parseFloat(cashHandedOver) || 0,
      discrepancies: discrepancies.filter((d) => d.amount > 0),
    });
  }

  const cashHandedOverNum = parseFloat(cashHandedOver) || 0;
  const expectedCash = selectedPhlebotomist?.cash_collected ?? 0;
  const approvedDeductions = discrepancies
    .filter((d) => d.type === "fuel_allowance" || d.type === "patient_refund")
    .reduce((sum, d) => sum + (d.amount || 0), 0);
  const netDiscrepancy = expectedCash - cashHandedOverNum - approvedDeductions;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Cash Reconciliation</h1>
          <p className="text-muted-foreground">
            Reconcile daily cash collections from phlebotomists
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      {pendingData && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending</CardTitle>
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{pendingData.items.length}</div>
              <p className="text-xs text-muted-foreground">phlebotomists to reconcile</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Cash</CardTitle>
              <DollarSign className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(
                  pendingData.items.reduce((s, i) => s + i.cash_collected, 0)
                )}
              </div>
              <p className="text-xs text-muted-foreground">to be collected</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Online Collected</CardTitle>
              <DollarSign className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(
                  pendingData.items.reduce((s, i) => s + i.online_collected, 0)
                )}
              </div>
              <p className="text-xs text-muted-foreground">via UPI/Card/Wallet</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Collection</CardTitle>
              <DollarSign className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(
                  pendingData.items.reduce((s, i) => s + i.total_collected, 0)
                )}
              </div>
              <p className="text-xs text-muted-foreground">all payment modes</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="pending">Pending Reconciliations</TabsTrigger>
          <TabsTrigger value="verification">Pending Verifications</TabsTrigger>
        </TabsList>

        {/* Pending Reconciliations Tab */}
        <TabsContent value="pending">
          <Card>
            <CardHeader>
              <CardTitle>Unreconciled Collections</CardTitle>
              <CardDescription>
                Cash collections awaiting reconciliation for {selectedDate}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {pendingLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  Loading...
                </div>
              ) : !pendingData?.items.length ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <CheckCircle className="mb-2 h-8 w-8 text-green-500" />
                  <p>All reconciliations complete for this date</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Phlebotomist</TableHead>
                      <TableHead className="text-right">Appointments</TableHead>
                      <TableHead className="text-right">Cash Collected</TableHead>
                      <TableHead className="text-right">Online Collected</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pendingData.items.map((item) => (
                      <TableRow key={item.phlebotomist_id}>
                        <TableCell className="font-medium">{item.name}</TableCell>
                        <TableCell className="text-right">
                          {item.total_appointments}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(item.cash_collected)}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(item.online_collected)}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(item.total_collected)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            size="sm"
                            onClick={() => openCreateDialog(item)}
                          >
                            <Plus className="mr-1 h-4 w-4" />
                            Reconcile
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Pending Verifications Tab */}
        <TabsContent value="verification">
          <Card>
            <CardHeader>
              <CardTitle>Pending Verifications</CardTitle>
              <CardDescription>
                Reconciliations awaiting admin verification
              </CardDescription>
            </CardHeader>
            <CardContent>
              {reportData ? (
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">Total Reconciliations</p>
                      <p className="text-2xl font-bold">{reportData.reconciliation_count}</p>
                    </div>
                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">Pending Verification</p>
                      <p className="text-2xl font-bold text-yellow-600">
                        {reportData.pending_count}
                      </p>
                    </div>
                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">Outstanding Dues</p>
                      <p className="text-2xl font-bold text-red-600">
                        {formatCurrency(reportData.outstanding_dues)}
                      </p>
                    </div>
                  </div>
                  {reportData.pending_count === 0 && (
                    <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                      <CheckCircle className="mb-2 h-8 w-8 text-green-500" />
                      <p>No pending verifications</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  Loading...
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create Reconciliation Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              Create Reconciliation — {selectedPhlebotomist?.name}
            </DialogTitle>
          </DialogHeader>

          {selectedPhlebotomist && (
            <div className="space-y-6">
              {/* Expected Summary */}
              <div className="rounded-lg border bg-muted/50 p-4">
                <h4 className="mb-2 font-medium">Collection Summary</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-muted-foreground">Cash Collected:</span>
                  <span className="font-medium">
                    {formatCurrency(selectedPhlebotomist.cash_collected)}
                  </span>
                  <span className="text-muted-foreground">Online Collected:</span>
                  <span className="font-medium">
                    {formatCurrency(selectedPhlebotomist.online_collected)}
                  </span>
                  <span className="text-muted-foreground">Total:</span>
                  <span className="font-bold">
                    {formatCurrency(selectedPhlebotomist.total_collected)}
                  </span>
                </div>
              </div>

              {/* Cash Handed Over Input */}
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  Cash Handed Over (₹)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={cashHandedOver}
                  onChange={(e) => setCashHandedOver(e.target.value)}
                  placeholder="Enter amount handed over"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>

              {/* Discrepancies */}
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-sm font-medium">Discrepancies</label>
                  <Button variant="outline" size="sm" onClick={addDiscrepancy}>
                    <Plus className="mr-1 h-3 w-3" />
                    Add
                  </Button>
                </div>
                {discrepancies.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No discrepancies added
                  </p>
                ) : (
                  <div className="space-y-3">
                    {discrepancies.map((disc, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-2 rounded-lg border p-3"
                      >
                        <div className="flex-1 space-y-2">
                          <div className="flex gap-2">
                            <select
                              value={disc.type}
                              onChange={(e) =>
                                updateDiscrepancy(idx, "type", e.target.value)
                              }
                              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                            >
                              {DISCREPANCY_TYPES.map((t) => (
                                <option key={t.value} value={t.value}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              value={disc.amount || ""}
                              onChange={(e) =>
                                updateDiscrepancy(
                                  idx,
                                  "amount",
                                  parseFloat(e.target.value) || 0
                                )
                              }
                              placeholder="Amount"
                              className="w-32 rounded-md border border-input bg-background px-3 py-2 text-sm"
                            />
                          </div>
                          <input
                            type="text"
                            value={disc.notes}
                            onChange={(e) =>
                              updateDiscrepancy(idx, "notes", e.target.value)
                            }
                            placeholder="Notes (optional)"
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                          />
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeDiscrepancy(idx)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Expected vs Actual */}
              <div className="rounded-lg border p-4">
                <h4 className="mb-2 font-medium">Reconciliation Summary</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-muted-foreground">Expected Cash:</span>
                  <span className="font-medium">{formatCurrency(expectedCash)}</span>
                  <span className="text-muted-foreground">Cash Handed Over:</span>
                  <span className="font-medium">
                    {formatCurrency(cashHandedOverNum)}
                  </span>
                  {approvedDeductions > 0 && (
                    <>
                      <span className="text-muted-foreground">
                        Approved Deductions:
                      </span>
                      <span className="font-medium text-blue-600">
                        -{formatCurrency(approvedDeductions)}
                      </span>
                    </>
                  )}
                  <span className="font-medium">Net Discrepancy:</span>
                  <span
                    className={`font-bold ${
                      netDiscrepancy === 0
                        ? "text-green-600"
                        : netDiscrepancy > 0
                          ? "text-red-600"
                          : "text-blue-600"
                    }`}
                  >
                    {formatCurrency(Math.abs(netDiscrepancy))}
                    {netDiscrepancy > 0
                      ? " (Short)"
                      : netDiscrepancy < 0
                        ? " (Over)"
                        : " (Balanced)"}
                  </span>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateDialog(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || !cashHandedOver}
            >
              {createMutation.isPending ? "Submitting..." : "Submit Reconciliation"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
