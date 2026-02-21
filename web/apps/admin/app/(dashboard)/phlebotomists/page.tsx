"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ColumnDef } from "@tanstack/react-table";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { Plus, Eye, MoreHorizontal, Pencil } from "lucide-react";
import api from "@/lib/api";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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

interface Phlebotomist {
  id: string;
  name: string;
  phone: string;
  email: string;
  status: "active" | "inactive";
  zones: Zone[];
  created_at: string;
}

interface PhlebotomistsResponse {
  data: Phlebotomist[];
  total: number;
}

interface ZonesResponse {
  data: Zone[];
}

// ---- Schema ----

const addPhlebotomistSchema = z.object({
  name: z.string().min(1, "Name is required"),
  phone: z.string().min(10, "Valid phone is required"),
  email: z.string().email("Valid email is required"),
  zone_ids: z.array(z.string()).optional(),
});

type AddPhlebotomistForm = z.infer<typeof addPhlebotomistSchema>;

// ---- API ----

function fetchPhlebotomists(params?: { search?: string; zone_id?: string }) {
  return api
    .get<PhlebotomistsResponse>("/phlebotomists", { params })
    .then((r) => r.data);
}

function fetchZones() {
  return api.get<ZonesResponse>("/zones").then((r) => r.data);
}

function createPhlebotomist(data: AddPhlebotomistForm) {
  return api.post("/phlebotomists", data).then((r) => r.data);
}

// ---- Component ----

export default function PhlebotomistsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const [zoneFilter, setZoneFilter] = React.useState("");

  const { data: phlebData, isLoading } = useQuery({
    queryKey: ["phlebotomists", search, zoneFilter],
    queryFn: () =>
      fetchPhlebotomists({
        search: search || undefined,
        zone_id: zoneFilter || undefined,
      }),
  });

  const { data: zonesData } = useQuery({
    queryKey: ["zones"],
    queryFn: fetchZones,
  });

  const zones = zonesData?.data ?? [];

  const createMutation = useMutation({
    mutationFn: createPhlebotomist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["phlebotomists"] });
      setOpen(false);
      form.reset();
    },
  });

  const form = useForm<AddPhlebotomistForm>({
    resolver: zodResolver(addPhlebotomistSchema),
    defaultValues: { name: "", phone: "", email: "", zone_ids: [] },
  });

  const columns: ColumnDef<Phlebotomist>[] = [
    { accessorKey: "name", header: "Name" },
    { accessorKey: "phone", header: "Phone" },
    {
      id: "zones",
      header: "Zones",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.zones?.length ? (
            row.original.zones.map((z) => (
              <Badge key={z.id} variant="secondary">
                {z.name}
              </Badge>
            ))
          ) : (
            <span className="text-gray-400 text-xs">No zones</span>
          )}
        </div>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge
          variant={row.original.status === "active" ? "default" : "outline"}
        >
          {row.original.status}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() =>
                router.push(`/phlebotomists/${row.original.id}`)
              }
            >
              <Eye className="mr-2 h-4 w-4" /> View
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() =>
                router.push(`/phlebotomists/${row.original.id}`)
              }
            >
              <Pencil className="mr-2 h-4 w-4" /> Edit
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Phlebotomists</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage phlebotomists, zone assignments, and documents.
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Add Phlebotomist
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Phlebotomist</DialogTitle>
            </DialogHeader>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}
                className="space-y-4"
              >
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <input
                          {...field}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                          placeholder="Full name"
                        />
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
                        <input
                          {...field}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                          placeholder="Phone number"
                        />
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
                        <input
                          {...field}
                          type="email"
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                          placeholder="Email address"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="zone_ids"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Zones (optional)</FormLabel>
                      <FormControl>
                        <select
                          multiple
                          value={field.value ?? []}
                          onChange={(e) =>
                            field.onChange(
                              Array.from(
                                e.target.selectedOptions,
                                (o) => o.value
                              )
                            )
                          }
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        >
                          {zones.map((z) => (
                            <option key={z.id} value={z.id}>
                              {z.name}
                            </option>
                          ))}
                        </select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <DialogFooter>
                  <Button
                    type="submit"
                    disabled={createMutation.isPending}
                  >
                    {createMutation.isPending ? "Creating…" : "Create"}
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <input
          placeholder="Search by name or phone…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
        <select
          value={zoneFilter}
          onChange={(e) => setZoneFilter(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All Zones</option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">Loading…</div>
      ) : (
        <DataTable columns={columns} data={phlebData?.data ?? []} />
      )}
    </div>
  );
}
