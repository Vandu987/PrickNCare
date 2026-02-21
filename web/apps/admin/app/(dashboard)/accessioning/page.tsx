"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Search,
  ScanBarcode,
  Camera,
  Package,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  ChevronRight,
  Plus,
  Minus,
} from "lucide-react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

// ── Types ──────────────────────────────────────────────

interface Patient {
  id: string;
  name: string;
  phone: string;
}

interface PendingSample {
  id: string;
  order_id: string;
  booking_id: string;
  patient: Patient;
  tests: { id: string; name: string; sample_type?: string }[];
  scheduled_date: string;
  status: string;
  barcode?: string;
  priority: "normal" | "urgent" | "stat";
}

interface ScannedOrder {
  id: string;
  order_id: string;
  booking_id: string;
  patient: Patient;
  tests: { id: string; name: string; sample_type?: string }[];
  status: string;
  barcode?: string;
  priority: "normal" | "urgent" | "stat";
  scheduled_date: string;
  accessioned?: boolean;
}

interface VialEntry {
  type: string;
  quantity: number;
}

interface AccessioningFormData {
  vials: VialEntry[];
  integrity: "intact" | "compromised" | "hemolyzed" | "lipemic" | "clotted";
  acceptance: "accepted" | "hold" | "rejected";
  notes: string;
  temperature_ok: boolean;
}

interface PendingResponse {
  items: PendingSample[];
  total: number;
}

// ── Constants ──────────────────────────────────────────

const VIAL_TYPES = [
  "EDTA (Purple)",
  "SST (Gold/Yellow)",
  "Citrate (Blue)",
  "Heparin (Green)",
  "Fluoride (Gray)",
  "Plain (Red)",
];

const INTEGRITY_OPTIONS = [
  { value: "intact", label: "Intact" },
  { value: "compromised", label: "Compromised" },
  { value: "hemolyzed", label: "Hemolyzed" },
  { value: "lipemic", label: "Lipemic" },
  { value: "clotted", label: "Clotted" },
];

const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  accepted: {
    color: "bg-green-100 text-green-800 border-green-200",
    icon: <CheckCircle2 className="h-4 w-4 text-green-600" />,
    label: "Accepted",
  },
  hold: {
    color: "bg-yellow-100 text-yellow-800 border-yellow-200",
    icon: <AlertTriangle className="h-4 w-4 text-yellow-600" />,
    label: "On Hold",
  },
  rejected: {
    color: "bg-red-100 text-red-800 border-red-200",
    icon: <XCircle className="h-4 w-4 text-red-600" />,
    label: "Rejected",
  },
};

const priorityColors: Record<string, string> = {
  normal: "bg-gray-100 text-gray-700",
  urgent: "bg-orange-100 text-orange-800",
  stat: "bg-red-100 text-red-800",
};

// ── API Functions ──────────────────────────────────────

async function fetchPendingSamples(): Promise<PendingResponse> {
  const { data } = await api.get("/accessioning/pending");
  return data.data ?? data;
}

async function scanBarcode(barcode: string): Promise<ScannedOrder> {
  const { data } = await api.get(`/accessioning/scan/${encodeURIComponent(barcode)}`);
  return data.data ?? data;
}

async function submitAccessioning(
  orderId: string,
  payload: AccessioningFormData
) {
  const { data } = await api.post(`/accessioning/${orderId}`, payload);
  return data;
}

// ── Page Component ─────────────────────────────────────

export default function AccessioningPage() {
  const queryClient = useQueryClient();

  // Barcode scanning
  const [barcodeInput, setBarcodeInput] = useState("");
  const [scanError, setScanError] = useState("");
  const [scannedOrder, setScannedOrder] = useState<ScannedOrder | null>(null);
  const barcodeRef = useRef<HTMLInputElement>(null);

  // Accessioning form dialog
  const [formOpen, setFormOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<PendingSample | ScannedOrder | null>(null);
  const [formData, setFormData] = useState<AccessioningFormData>({
    vials: [{ type: VIAL_TYPES[0], quantity: 1 }],
    integrity: "intact",
    acceptance: "accepted",
    notes: "",
    temperature_ok: true,
  });

  // Camera scanner
  const [cameraActive, setCameraActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Queries
  const { data: pendingData, isLoading: pendingLoading } = useQuery({
    queryKey: ["accessioning-pending"],
    queryFn: fetchPendingSamples,
    refetchInterval: 30000,
  });

  const pendingSamples = pendingData?.items ?? [];

  // Scan mutation
  const scanMutation = useMutation({
    mutationFn: (barcode: string) => scanBarcode(barcode),
    onSuccess: (data) => {
      setScannedOrder(data);
      setScanError("");
    },
    onError: () => {
      setScanError("No order found for this barcode/ID");
      setScannedOrder(null);
    },
  });

  // Submit accessioning mutation
  const accessionMutation = useMutation({
    mutationFn: ({
      orderId,
      payload,
    }: {
      orderId: string;
      payload: AccessioningFormData;
    }) => submitAccessioning(orderId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accessioning-pending"] });
      setFormOpen(false);
      setSelectedOrder(null);
      setScannedOrder(null);
      setBarcodeInput("");
      resetForm();
    },
  });

  // ── Helpers ──────────────────────────────────────────

  const resetForm = () => {
    setFormData({
      vials: [{ type: VIAL_TYPES[0], quantity: 1 }],
      integrity: "intact",
      acceptance: "accepted",
      notes: "",
      temperature_ok: true,
    });
  };

  const openAccessionForm = (order: PendingSample | ScannedOrder) => {
    setSelectedOrder(order);
    resetForm();
    setFormOpen(true);
  };

  const handleScan = useCallback(() => {
    const val = barcodeInput.trim();
    if (!val) return;
    setScanError("");
    scanMutation.mutate(val);
  }, [barcodeInput, scanMutation]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleScan();
    }
  };

  // Vial management
  const addVial = () => {
    setFormData((prev) => ({
      ...prev,
      vials: [...prev.vials, { type: VIAL_TYPES[0], quantity: 1 }],
    }));
  };

  const removeVial = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      vials: prev.vials.filter((_, i) => i !== index),
    }));
  };

  const updateVial = (index: number, field: keyof VialEntry, value: string | number) => {
    setFormData((prev) => ({
      ...prev,
      vials: prev.vials.map((v, i) => (i === index ? { ...v, [field]: value } : v)),
    }));
  };

  // Camera handling
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraActive(true);
    } catch {
      setScanError("Camera access denied or unavailable. Use manual input.");
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  // Focus barcode input on mount
  useEffect(() => {
    barcodeRef.current?.focus();
  }, []);

  // ── Render ───────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sample Accessioning</h1>
        <p className="mt-1 text-sm text-gray-500">
          Scan barcodes or search booking IDs to accession incoming samples.
        </p>
      </div>

      {/* Barcode Scanner Section */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <ScanBarcode className="h-5 w-5" />
            Scan / Search
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                ref={barcodeRef}
                placeholder="Scan barcode or enter booking ID..."
                value={barcodeInput}
                onChange={(e) => {
                  setBarcodeInput(e.target.value);
                  setScanError("");
                }}
                onKeyDown={handleKeyDown}
                className="w-full rounded-md border border-gray-300 py-2.5 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                autoFocus
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleScan}
                disabled={!barcodeInput.trim() || scanMutation.isPending}
                className="gap-2"
              >
                {scanMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                Search
              </Button>
              <Button
                variant="outline"
                onClick={cameraActive ? stopCamera : startCamera}
                className="gap-2"
              >
                <Camera className="h-4 w-4" />
                {cameraActive ? "Stop Camera" : "Camera"}
              </Button>
            </div>
          </div>

          {/* Camera Preview */}
          {cameraActive && (
            <div className="relative overflow-hidden rounded-md border bg-black">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                className="h-48 w-full object-cover"
              />
              <p className="absolute bottom-2 left-2 rounded bg-black/70 px-2 py-1 text-xs text-white">
                Point camera at barcode — or type the code manually above
              </p>
            </div>
          )}

          {/* Scan Error */}
          {scanError && (
            <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              <XCircle className="h-4 w-4 shrink-0" />
              {scanError}
            </div>
          )}

          {/* Scanned Result */}
          {scannedOrder && (
            <div className="rounded-md border border-primary-200 bg-primary-50 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900">
                      {scannedOrder.booking_id}
                    </h3>
                    <Badge className={priorityColors[scannedOrder.priority] ?? ""}>
                      {scannedOrder.priority}
                    </Badge>
                    {scannedOrder.accessioned && (
                      <Badge className="bg-green-100 text-green-800">Already Accessioned</Badge>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-gray-600">
                    Patient: {scannedOrder.patient?.name} — {scannedOrder.patient?.phone}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {scannedOrder.tests?.map((t) => (
                      <Badge key={t.id} variant="outline" className="text-xs">
                        {t.name}
                        {t.sample_type && ` (${t.sample_type})`}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" asChild variant="outline">
                    <Link href={`/accessioning/${scannedOrder.id}`}>Details</Link>
                  </Button>
                  {!scannedOrder.accessioned && (
                    <Button size="sm" onClick={() => openAccessionForm(scannedOrder)}>
                      Accession
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pending Samples */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Package className="h-5 w-5" />
            Pending Samples
            {pendingData && (
              <Badge variant="secondary" className="ml-2">
                {pendingData.total}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pendingLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : pendingSamples.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-500">
              No pending samples for accessioning.
            </div>
          ) : (
            <div className="divide-y">
              {pendingSamples.map((sample) => (
                <div
                  key={sample.id}
                  className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/accessioning/${sample.id}`}
                        className="font-medium text-primary-600 hover:underline"
                      >
                        {sample.booking_id}
                      </Link>
                      <Badge className={priorityColors[sample.priority] ?? ""}>
                        {sample.priority}
                      </Badge>
                      {sample.barcode && (
                        <span className="font-mono text-xs text-gray-400">
                          {sample.barcode}
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-sm text-gray-600">
                      {sample.patient?.name} — {sample.scheduled_date}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {sample.tests?.slice(0, 3).map((t) => (
                        <Badge key={t.id} variant="outline" className="text-xs">
                          {t.name}
                        </Badge>
                      ))}
                      {(sample.tests?.length ?? 0) > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{sample.tests.length - 3} more
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="ml-4 flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={() => openAccessionForm(sample)}
                    >
                      Accession
                    </Button>
                    <Link href={`/accessioning/${sample.id}`}>
                      <ChevronRight className="h-4 w-4 text-gray-400" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Accessioning Form Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Accession Sample</DialogTitle>
          </DialogHeader>
          {selectedOrder && (
            <div className="space-y-4">
              {/* Order Summary */}
              <div className="rounded-md border bg-gray-50 p-3 text-sm">
                <p>
                  <span className="font-medium">Booking:</span>{" "}
                  {selectedOrder.booking_id}
                </p>
                <p>
                  <span className="font-medium">Patient:</span>{" "}
                  {selectedOrder.patient?.name}
                </p>
                <p>
                  <span className="font-medium">Tests:</span>{" "}
                  {selectedOrder.tests?.map((t) => t.name).join(", ")}
                </p>
              </div>

              {/* Vials */}
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Vials Received
                </label>
                <div className="space-y-2">
                  {formData.vials.map((vial, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <select
                        value={vial.type}
                        onChange={(e) => updateVial(idx, "type", e.target.value)}
                        className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        {VIAL_TYPES.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() =>
                            updateVial(idx, "quantity", Math.max(1, vial.quantity - 1))
                          }
                          className="rounded border p-1 hover:bg-gray-100"
                        >
                          <Minus className="h-3 w-3" />
                        </button>
                        <span className="w-8 text-center text-sm">{vial.quantity}</span>
                        <button
                          type="button"
                          onClick={() => updateVial(idx, "quantity", vial.quantity + 1)}
                          className="rounded border p-1 hover:bg-gray-100"
                        >
                          <Plus className="h-3 w-3" />
                        </button>
                      </div>
                      {formData.vials.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeVial(idx)}
                          className="rounded p-1 text-red-500 hover:bg-red-50"
                        >
                          <XCircle className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addVial}
                    className="gap-1"
                  >
                    <Plus className="h-3 w-3" /> Add Vial
                  </Button>
                </div>
              </div>

              {/* Integrity */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Sample Integrity
                </label>
                <select
                  value={formData.integrity}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      integrity: e.target.value as AccessioningFormData["integrity"],
                    }))
                  }
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {INTEGRITY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Temperature */}
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formData.temperature_ok}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, temperature_ok: e.target.checked }))
                  }
                  className="rounded border-gray-300"
                />
                Temperature within acceptable range
              </label>

              {/* Acceptance Status */}
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Acceptance Status
                </label>
                <div className="flex gap-2">
                  {(["accepted", "hold", "rejected"] as const).map((status) => {
                    const cfg = statusConfig[status];
                    const isSelected = formData.acceptance === status;
                    return (
                      <button
                        key={status}
                        type="button"
                        onClick={() =>
                          setFormData((prev) => ({ ...prev, acceptance: status }))
                        }
                        className={`flex flex-1 items-center justify-center gap-1.5 rounded-md border-2 px-3 py-2 text-sm font-medium transition ${
                          isSelected
                            ? `${cfg.color} border-current`
                            : "border-gray-200 text-gray-500 hover:border-gray-300"
                        }`}
                      >
                        {cfg.icon}
                        {cfg.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Notes
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, notes: e.target.value }))
                  }
                  placeholder="Any observations or issues..."
                  rows={2}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              {accessionMutation.isError && (
                <p className="text-sm text-red-600">
                  Failed to submit accessioning. Please try again.
                </p>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={accessionMutation.isPending}
              onClick={() => {
                if (selectedOrder) {
                  accessionMutation.mutate({
                    orderId: selectedOrder.id,
                    payload: formData,
                  });
                }
              }}
            >
              {accessionMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                "Submit Accessioning"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
