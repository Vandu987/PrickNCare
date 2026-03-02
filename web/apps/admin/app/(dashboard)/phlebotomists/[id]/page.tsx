"use client";

import * as React from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ArrowLeft,
  Upload,
  Trash2,
  Plus,
  FileText,
  X,
} from "lucide-react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

// ---- Types ----

interface Zone {
  id: string;
  name: string;
}

interface Document {
  id: string;
  name: string;
  file_url: string;
  type: string;
  uploaded_at: string;
}

interface Phlebotomist {
  id: string;
  name: string;
  phone: string;
  email: string;
  status: "active" | "inactive";
  zones: Zone[];
  documents: Document[];
  created_at: string;
}

interface PerformanceStats {
  total_bookings: number;
  completed_bookings: number;
  cancelled_bookings: number;
  avg_rating: number;
  on_time_percentage: number;
  total_revenue: number;
}

interface ZonesResponse {
  data: Zone[];
}

// ---- Schemas ----

const profileSchema = z.object({
  name: z.string().min(1, "Name is required"),
  phone: z.string().min(10, "Valid phone is required"),
  email: z.string().email("Valid email is required"),
  status: z.enum(["active", "inactive"]),
});

type ProfileForm = z.infer<typeof profileSchema>;

// ---- API helpers ----

function fetchPhlebotomist(id: string) {
  return api.get(`/phlebotomists/${id}`).then((r) => r.data?.data ?? r.data);
}

function updatePhlebotomist(id: string, data: ProfileForm) {
  return api.put(`/phlebotomists/${id}`, data).then((r) => r.data);
}

function fetchAllZones() {
  return api.get("/zones").then((r) => r.data?.data ?? r.data?.items ?? r.data);
}

function assignZone(phlebId: string, zoneId: string) {
  return api.post(`/phlebotomists/${phlebId}/zones`, { zone_id: zoneId }).then((r) => r.data);
}

function removeZone(phlebId: string, zoneId: string) {
  return api.delete(`/phlebotomists/${phlebId}/zones/${zoneId}`).then((r) => r.data);
}

function uploadDocument(phlebId: string, file: File, docType: string) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("type", docType);
  fd.append("entity_type", "phlebotomist");
  fd.append("entity_id", phlebId);
  return api
    .post("/files/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
}

function deleteDocument(docId: string) {
  return api.delete(`/files/${docId}`).then((r) => r.data);
}

function fetchPerformance(phlebId: string) {
  return api
    .get(`/reports/phlebotomist-performance`, {
      params: { phlebotomist_id: phlebId },
    })
    .then((r) => r.data?.data ?? r.data);
}

// ---- Profile Tab ----

function ProfileTab({
  phleb,
  onSaved,
  readOnly = false,
}: {
  phleb: Phlebotomist;
  onSaved: () => void;
  readOnly?: boolean;
}) {
  const form = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: phleb.name,
      phone: phleb.phone,
      email: phleb.email,
      status: phleb.status,
    },
  });

  const mutation = useMutation({
    mutationFn: (data: ProfileForm) => updatePhlebotomist(phleb.id, data),
    onSuccess: onSaved,
  });

  if (readOnly) {
    return (
      <Card className="p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-medium text-gray-500">Name</p>
            <p className="mt-1 text-sm text-gray-900">{phleb.name}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500">Phone</p>
            <p className="mt-1 text-sm text-gray-900">{phleb.phone}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500">Email</p>
            <p className="mt-1 text-sm text-gray-900">{phleb.email}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500">Status</p>
            <Badge variant={phleb.status === "active" ? "default" : "outline"} className="mt-1">
              {phleb.status}
            </Badge>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500">Zones</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {phleb.zones?.length ? phleb.zones.map((z: Zone) => (
                <Badge key={z.id} variant="secondary">{z.name}</Badge>
              )) : <span className="text-sm text-gray-400">No zones</span>}
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500">Created</p>
            <p className="mt-1 text-sm text-gray-900">
              {phleb.created_at ? new Date(phleb.created_at).toLocaleDateString("en-IN") : "—"}
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
        >
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Name</FormLabel>
                <FormControl>
                  <input {...field} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="phone"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Phone</FormLabel>
                <FormControl>
                  <input {...field} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <input {...field} type="email" className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="status"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Status</FormLabel>
                <FormControl>
                  <select {...field} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <div className="sm:col-span-2">
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : "Save Changes"}
            </Button>
          </div>
        </form>
      </Form>
    </Card>
  );
}

// ---- Zones Tab ----

function ZonesTab({ phleb }: { phleb: Phlebotomist }) {
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = React.useState(false);
  const [selectedZone, setSelectedZone] = React.useState("");

  const { data: allZones } = useQuery({
    queryKey: ["zones"],
    queryFn: fetchAllZones,
  });

  const zonesList: Zone[] = Array.isArray(allZones) ? allZones : (allZones as any)?.items ?? (allZones as any)?.data ?? [];
  const assignedIds = new Set(phleb.zones?.map((z: Zone) => z.id) ?? []);
  const availableZones = zonesList.filter((z: Zone) => !assignedIds.has(z.id));

  const assignMutation = useMutation({
    mutationFn: (zoneId: string) => assignZone(phleb.id, zoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["phlebotomist", phleb.id] });
      setAddOpen(false);
      setSelectedZone("");
    },
  });

  const removeMutation = useMutation({
    mutationFn: (zoneId: string) => removeZone(phleb.id, zoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["phlebotomist", phleb.id] });
    },
  });

  return (
    <Card className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Assigned Zones</h3>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="mr-1 h-4 w-4" /> Add Zone
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Assign Zone</DialogTitle>
            </DialogHeader>
            <select
              value={selectedZone}
              onChange={(e) => setSelectedZone(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select a zone</option>
              {availableZones.map((z: Zone) => (
                <option key={z.id} value={z.id}>
                  {z.name}
                </option>
              ))}
            </select>
            <DialogFooter>
              <Button
                disabled={!selectedZone || assignMutation.isPending}
                onClick={() => assignMutation.mutate(selectedZone)}
              >
                {assignMutation.isPending ? "Assigning…" : "Assign"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {phleb.zones?.length ? (
        <div className="space-y-2">
          {phleb.zones.map((z) => (
            <div
              key={z.id}
              className="flex items-center justify-between rounded-md border px-4 py-2"
            >
              <span className="text-sm font-medium">{z.name}</span>
              <button
                onClick={() => removeMutation.mutate(z.id)}
                disabled={removeMutation.isPending}
                className="text-red-500 hover:text-red-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-400">No zones assigned.</p>
      )}
    </Card>
  );
}

// ---- Documents Tab ----

function DocumentsTab({ phleb }: { phleb: Phlebotomist }) {
  const queryClient = useQueryClient();
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [docType, setDocType] = React.useState("id_proof");

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(phleb.id, file, docType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["phlebotomist", phleb.id] });
      if (fileRef.current) fileRef.current.value = "";
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["phlebotomist", phleb.id] });
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) uploadMutation.mutate(file);
  }

  return (
    <Card className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Documents</h3>
        <div className="flex items-center gap-2">
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="id_proof">ID Proof</option>
            <option value="certification">Certification</option>
            <option value="address_proof">Address Proof</option>
            <option value="other">Other</option>
          </select>
          <Button
            size="sm"
            onClick={() => fileRef.current?.click()}
            disabled={uploadMutation.isPending}
          >
            <Upload className="mr-1 h-4 w-4" />
            {uploadMutation.isPending ? "Uploading…" : "Upload"}
          </Button>
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
          />
        </div>
      </div>

      {phleb.documents?.length ? (
        <div className="space-y-2">
          {phleb.documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between rounded-md border px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-gray-400" />
                <div>
                  <a
                    href={doc.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-blue-600 hover:underline"
                  >
                    {doc.name}
                  </a>
                  <p className="text-xs text-gray-400">
                    {doc.type} · {new Date(doc.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <button
                onClick={() => deleteMutation.mutate(doc.id)}
                disabled={deleteMutation.isPending}
                className="text-red-500 hover:text-red-700"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-400">No documents uploaded.</p>
      )}
    </Card>
  );
}

// ---- Performance Tab ----

function PerformanceTab({ phlebId }: { phlebId: string }) {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["phlebotomist-performance", phlebId],
    queryFn: () => fetchPerformance(phlebId),
  });

  if (isLoading) {
    return <div className="py-8 text-center text-gray-400">Loading performance data…</div>;
  }

  if (!stats) {
    return <div className="py-8 text-center text-gray-400">No performance data available.</div>;
  }

  const cards = [
    { label: "Total Bookings", value: stats.total_bookings },
    { label: "Completed", value: stats.completed_bookings },
    { label: "Cancelled", value: stats.cancelled_bookings },
    { label: "Avg Rating", value: stats.avg_rating?.toFixed(1) ?? "N/A" },
    { label: "On-Time %", value: `${stats.on_time_percentage?.toFixed(0) ?? 0}%` },
    { label: "Revenue", value: `₹${stats.total_revenue?.toLocaleString() ?? 0}` },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      {cards.map((c) => (
        <Card key={c.label} className="p-4 text-center">
          <p className="text-sm text-gray-500">{c.label}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{c.value}</p>
        </Card>
      ))}
    </div>
  );
}

// ---- Main Page ----

export default function PhlebotomistDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const isViewMode = searchParams.get("mode") !== "edit";

  const { data: phleb, isLoading } = useQuery({
    queryKey: ["phlebotomist", params.id],
    queryFn: () => fetchPhlebotomist(params.id),
    enabled: !!params.id,
  });

  if (isLoading) {
    return <div className="py-12 text-center text-gray-400">Loading…</div>;
  }

  if (!phleb) {
    return <div className="py-12 text-center text-gray-500">Phlebotomist not found.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push("/phlebotomists")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{phleb.name}</h1>
          <p className="text-sm text-gray-500">{phleb.phone} · {phleb.email}</p>
        </div>
        <Badge variant={phleb.status === "active" ? "default" : "outline"} className="ml-auto">
          {phleb.status}
        </Badge>
      </div>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="zones">Zones</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <ProfileTab
            phleb={phleb}
            readOnly={isViewMode}
            onSaved={() =>
              queryClient.invalidateQueries({
                queryKey: ["phlebotomist", params.id],
              })
            }
          />
        </TabsContent>

        <TabsContent value="zones">
          <ZonesTab phleb={phleb} />
        </TabsContent>

        <TabsContent value="documents">
          <DocumentsTab phleb={phleb} />
        </TabsContent>

        <TabsContent value="performance">
          <PerformanceTab phlebId={phleb.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
