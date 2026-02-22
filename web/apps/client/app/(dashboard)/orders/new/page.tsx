"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Package } from "@/types";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Plus,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle2,
  IndianRupee,
} from "lucide-react";

// ── Zod Schema ──

const patientSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  age: z.number().min(0, "Age must be positive").max(150, "Invalid age"),
  gender: z.enum(["M", "F", "O"], { message: "Select gender" }),
  phone: z
    .string()
    .regex(/^[6-9]\d{9}$/, "Enter valid 10-digit mobile number"),
  package_ids: z
    .array(z.number())
    .min(1, "Select at least one package"),
});

const orderFormSchema = z.object({
  patients: z.array(patientSchema).min(1, "Add at least one patient"),
  collection_address: z.string().min(5, "Enter full address"),
  pincode: z.string().regex(/^\d{6}$/, "Enter valid 6-digit pincode"),
  locality: z.string().min(1, "Select locality"),
  city: z.string().min(1, "City is required"),
  scheduled_date: z.string().min(1, "Select date"),
  scheduled_time_slot: z.string().min(1, "Select time slot"),
  priority: z.enum(["normal", "high"]),
  payment_mode: z.enum(["cash", "upi", "card", "wallet", "postpaid"], {
    message: "Select payment mode",
  }),
  notes: z.string().optional(),
});

type OrderFormValues = z.infer<typeof orderFormSchema>;

// ── Interfaces ──

interface PincodeResult {
  id: string;
  pincode: string;
  zone_name: string;
  city_name: string;
  locality?: string;
  city?: string;
}

interface PricingBreakdown {
  first_collection: number;
  additional_collections: number;
  priority_fee: number;
  total: number;
  package_details: { id: number; name: string; price: number }[];
}

const TIME_SLOTS = [
  "06:00 - 08:00",
  "08:00 - 10:00",
  "10:00 - 12:00",
  "12:00 - 14:00",
  "14:00 - 16:00",
  "16:00 - 18:00",
];

const PAYMENT_MODES = [
  { value: "cash", label: "Cash" },
  { value: "upi", label: "UPI" },
  { value: "card", label: "Card" },
  { value: "wallet", label: "Wallet" },
  { value: "postpaid", label: "Postpaid" },
] as const;

// ── Component ──

export default function NewOrderPage() {
  const router = useRouter();
  const [pincodeQuery, setPincodeQuery] = useState("");
  const [localities, setLocalities] = useState<PincodeResult[]>([]);
  const [selectedPackageIds, setSelectedPackageIds] = useState<Set<number>>(
    new Set()
  );

  const form = useForm<OrderFormValues>({
    resolver: zodResolver(orderFormSchema),
    defaultValues: {
      patients: [
        { name: "", age: 0, gender: "M", phone: "", package_ids: [] },
      ],
      collection_address: "",
      pincode: "",
      locality: "",
      city: "",
      scheduled_date: "",
      scheduled_time_slot: "",
      priority: "normal",
      payment_mode: "cash",
      notes: "",
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "patients",
  });

  const priority = form.watch("priority");

  // ── Packages Query ──
  const { data: packages = [] } = useQuery<Package[]>({
    queryKey: ["packages"],
    queryFn: async () => {
      const { data } = await api.get("/packages", {
        params: { is_active: true },
      });
      return data.results ?? data;
    },
  });

  // ── Pincode Suggest ──
  const { data: pincodeSuggestions = [] } = useQuery<PincodeResult[]>({
    queryKey: ["pincodes", pincodeQuery],
    queryFn: async () => {
      const { data } = await api.get("/pincodes/suggest", {
        params: { q: pincodeQuery },
      });
      const results = data.results ?? data;
      return results.map((r: PincodeResult) => ({ ...r, city: r.city_name ?? r.city, locality: r.zone_name ?? r.locality }));
    },
    enabled: pincodeQuery.length >= 3,
  });

  // ── Collect all selected package IDs across patients ──
  const allPatients = form.watch("patients");
  const computeSelectedIds = useCallback(() => {
    const ids = new Set<number>();
    allPatients.forEach((p) => p.package_ids?.forEach((id) => ids.add(id)));
    return ids;
  }, [allPatients]);

  useEffect(() => {
    setSelectedPackageIds(computeSelectedIds());
  }, [computeSelectedIds]);

  // ── Pricing Query ──
  const { data: pricing, isFetching: pricingLoading } =
    useQuery<PricingBreakdown>({
      queryKey: [
        "pricing",
        Array.from(selectedPackageIds).sort().join(","),
        priority,
      ],
      queryFn: async () => {
        const { data } = await api.post("/pricing/calculate", {
          package_ids: Array.from(selectedPackageIds),
          priority,
        });
        return data;
      },
      enabled: selectedPackageIds.size > 0,
    });

  // ── Submit Order ──
  const createOrder = useMutation({
    mutationFn: async (values: OrderFormValues) => {
      const { data } = await api.post("/orders", values);
      return data;
    },
    onSuccess: (data) => {
      router.push(`/orders/${data.id}`);
    },
  });

  function onSubmit(values: OrderFormValues) {
    createOrder.mutate(values);
  }

  // ── Pincode handlers ──
  function handlePincodeChange(value: string) {
    form.setValue("pincode", value);
    if (value.length >= 3) {
      setPincodeQuery(value);
    }
  }

  async function selectPincode(result: PincodeResult) {
    form.setValue("pincode", result.pincode);
    form.setValue("city", result.city_name ?? result.city ?? "");
    setPincodeQuery("");
    // Fetch localities for this pincode
    try {
      const { data } = await api.get(`/localities/by-pincode/${result.pincode}`);
      const locs = (data ?? []).map((l: { name: string }) => ({
        ...result,
        locality: l.name,
      }));
      setLocalities(locs);
      if (locs.length === 1) {
        form.setValue("locality", locs[0].locality);
      }
    } catch {
      setLocalities([{ ...result, locality: result.zone_name ?? "Default" }]);
    }
  }

  // ── Package toggle for a patient ──
  function togglePackage(patientIndex: number, packageId: number) {
    const current = form.getValues(`patients.${patientIndex}.package_ids`);
    const next = current.includes(packageId)
      ? current.filter((id) => id !== packageId)
      : [...current, packageId];
    form.setValue(`patients.${patientIndex}.package_ids`, next, {
      shouldValidate: true,
    });
  }

  // ── Min date (tomorrow) ──
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const minDate = tomorrow.toISOString().split("T")[0];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Create New Order</h1>
        <p className="text-muted-foreground">
          Fill in patient details, select packages, and schedule collection.
        </p>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* ── Patients ── */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Patient Details</CardTitle>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  append({
                    name: "",
                    age: 0,
                    gender: "M",
                    phone: "",
                    package_ids: [],
                  })
                }
              >
                <Plus className="mr-1 h-4 w-4" /> Add Patient
              </Button>
            </CardHeader>
            <CardContent className="space-y-6">
              {fields.map((field, index) => (
                <div
                  key={field.id}
                  className="space-y-4 rounded-lg border p-4 relative"
                >
                  {fields.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-2 top-2 text-destructive"
                      onClick={() => remove(index)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}

                  <div className="text-sm font-medium text-muted-foreground">
                    Patient {index + 1}
                  </div>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <FormField
                      control={form.control}
                      name={`patients.${index}.name`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Name</FormLabel>
                          <FormControl>
                            <Input placeholder="Patient name" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name={`patients.${index}.age`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Age</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min={0}
                              max={150}
                              placeholder="Age"
                              {...field}
                              onChange={(e) =>
                                field.onChange(
                                  e.target.value === ""
                                    ? 0
                                    : Number(e.target.value)
                                )
                              }
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name={`patients.${index}.gender`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Gender</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            value={field.value}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Gender" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="M">Male</SelectItem>
                              <SelectItem value="F">Female</SelectItem>
                              <SelectItem value="O">Other</SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name={`patients.${index}.phone`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Phone</FormLabel>
                          <FormControl>
                            <Input
                              placeholder="10-digit mobile"
                              maxLength={10}
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* Package Selection */}
                  <FormField
                    control={form.control}
                    name={`patients.${index}.package_ids`}
                    render={() => (
                      <FormItem>
                        <FormLabel>Packages</FormLabel>
                        <div className="flex flex-wrap gap-2">
                          {packages.map((pkg) => {
                            const isSelected = form
                              .watch(`patients.${index}.package_ids`)
                              .includes(pkg.id);
                            return (
                              <button
                                key={pkg.id}
                                type="button"
                                onClick={() => togglePackage(index, pkg.id)}
                                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors ${
                                  isSelected
                                    ? "border-primary bg-primary/10 text-primary"
                                    : "border-border hover:border-primary/50"
                                }`}
                              >
                                {isSelected && (
                                  <CheckCircle2 className="h-3.5 w-3.5" />
                                )}
                                {pkg.name}
                                <Badge variant="secondary" className="ml-1 text-xs">
                                  {pkg.sample_type}
                                </Badge>
                              </button>
                            );
                          })}
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              ))}
            </CardContent>
          </Card>

          {/* ── Address ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Collection Address</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="collection_address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Address</FormLabel>
                    <FormControl>
                      <Input placeholder="House/Flat, Street, Area" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {/* Pincode with auto-suggest */}
                <FormField
                  control={form.control}
                  name="pincode"
                  render={({ field }) => (
                    <FormItem className="relative">
                      <FormLabel>Pincode</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="6-digit pincode"
                          maxLength={6}
                          {...field}
                          onChange={(e) => handlePincodeChange(e.target.value)}
                        />
                      </FormControl>
                      {pincodeSuggestions.length > 0 &&
                        pincodeQuery.length >= 3 && (
                          <div className="absolute top-full z-10 mt-1 w-full rounded-md border bg-popover shadow-md">
                            {pincodeSuggestions.map((s, i) => (
                              <button
                                key={`${s.pincode}-${s.zone_name}-${i}`}
                                type="button"
                                className="w-full px-3 py-2 text-left text-sm hover:bg-accent"
                                onClick={() => selectPincode(s)}
                              >
                                {s.pincode} — {s.zone_name}, {s.city_name}
                              </button>
                            ))}
                          </div>
                        )}
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="locality"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Locality</FormLabel>
                      {localities.length > 0 ? (
                        <Select
                          onValueChange={field.onChange}
                          value={field.value}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select locality" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {localities.map((l, i) => (
                              <SelectItem
                                key={`${l.locality ?? i}-${i}`}
                                value={l.locality ?? ""}
                              >
                                {l.locality ?? "Unknown"}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <FormControl>
                          <Input placeholder="Locality" {...field} />
                        </FormControl>
                      )}
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="city"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>City</FormLabel>
                      <FormControl>
                        <Input placeholder="City" {...field} readOnly />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          {/* ── Appointment ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Appointment</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="scheduled_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Date</FormLabel>
                      <FormControl>
                        <Input type="date" min={minDate} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="scheduled_time_slot"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Time Slot</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select time slot" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {TIME_SLOTS.map((slot) => (
                            <SelectItem key={slot} value={slot}>
                              {slot}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          {/* ── Priority & Payment ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Priority & Payment</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="priority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Priority</FormLabel>
                      <div className="flex gap-2">
                        {(["normal", "high"] as const).map((p) => (
                          <button
                            key={p}
                            type="button"
                            onClick={() => field.onChange(p)}
                            className={`flex-1 rounded-md border px-4 py-2 text-sm font-medium transition-colors ${
                              field.value === p
                                ? p === "high"
                                  ? "border-orange-500 bg-orange-500/10 text-orange-600"
                                  : "border-primary bg-primary/10 text-primary"
                                : "border-border hover:border-primary/50"
                            }`}
                          >
                            {p === "high" ? "⚡ High Priority" : "Normal"}
                          </button>
                        ))}
                      </div>
                      {field.value === "high" && (
                        <p className="text-xs text-orange-600">
                          High priority adds an additional fee for faster
                          processing.
                        </p>
                      )}
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="payment_mode"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Payment Mode</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select payment mode" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {PAYMENT_MODES.map((mode) => (
                            <SelectItem key={mode.value} value={mode.value}>
                              {mode.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          {/* ── Notes ── */}
          <FormField
            control={form.control}
            name="notes"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Notes (optional)</FormLabel>
                <FormControl>
                  <Input placeholder="Any special instructions..." {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* ── Pricing Breakdown ── */}
          {selectedPackageIds.size > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <IndianRupee className="h-5 w-5" />
                  Pricing Breakdown
                  {pricingLoading && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {pricing ? (
                  <div className="space-y-2 text-sm">
                    {pricing.package_details?.map((pkg) => (
                      <div
                        key={pkg.id}
                        className="flex justify-between text-muted-foreground"
                      >
                        <span>{pkg.name}</span>
                        <span>₹{pkg.price}</span>
                      </div>
                    ))}
                    <div className="border-t pt-2 space-y-1">
                      <div className="flex justify-between">
                        <span>First Collection</span>
                        <span>₹{pricing.first_collection}</span>
                      </div>
                      {pricing.additional_collections > 0 && (
                        <div className="flex justify-between">
                          <span>Additional Collections</span>
                          <span>₹{pricing.additional_collections}</span>
                        </div>
                      )}
                      {pricing.priority_fee > 0 && (
                        <div className="flex justify-between text-orange-600">
                          <span>Priority Fee</span>
                          <span>₹{pricing.priority_fee}</span>
                        </div>
                      )}
                    </div>
                    <div className="flex justify-between border-t pt-2 text-base font-semibold">
                      <span>Total</span>
                      <span>₹{pricing.total}</span>
                    </div>
                  </div>
                ) : (
                  !pricingLoading && (
                    <p className="text-sm text-muted-foreground">
                      Select packages to see pricing.
                    </p>
                  )
                )}
              </CardContent>
            </Card>
          )}

          {/* ── Submit ── */}
          {createOrder.isError && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              {(createOrder.error as Error)?.message ||
                "Failed to create order. Please try again."}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createOrder.isPending}>
              {createOrder.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Create Order
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
