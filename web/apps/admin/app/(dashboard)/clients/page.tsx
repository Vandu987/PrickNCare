"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ColumnDef } from "@tanstack/react-table";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Plus,
  MoreHorizontal,
  Eye,
  Pencil,
  Search,
} from "lucide-react";
import api from "@/lib/api";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
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

// ── Types ──────────────────────────────────────────────

interface Client {
  id: string;
  name: string;
  contact_person: string;
  contact_phone: string;
  contact_email: string;
  city: string;
  address: string;
  rate_first_collection: number;
  rate_second_collection: number;
  rate_priority: number;
  status: "active" | "inactive" | "suspended";
  created_at: string;
}

interface ClientsResponse {
  items: Client[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Validation ─────────────────────────────────────────

const clientSchema = z.object({
  name: z.string().min(1, "Name is required"),
  contact_person: z.string().min(1, "Contact person is required"),
  contact_phone: z.string().min(10, "Valid phone number required"),
  contact_email: z.string().email("Valid email required"),
  city: z.string().min(1, "City is required"),
  address: z.string().min(1, "Address is required"),
  rate_first_collection: z.number().min(0, "Must be >= 0"),
  rate_second_collection: z.number().min(0, "Must be >= 0"),
  rate_priority: z.number().min(0, "Must be >= 0"),
  status: z.enum(["active", "inactive", "suspended"]),
});

type ClientFormValues = z.infer<typeof clientSchema>;

// ── API ────────────────────────────────────────────────

async function fetchClients(params: {
  page: number;
  search: string;
  city: string;
  status: string;
}): Promise<ClientsResponse> {
  const query = new URLSearchParams();
  query.set("page", String(params.page));
  query.set("page_size", "10");
  if (params.search) query.set("search", params.search);
  if (params.city) query.set("city", params.city);
  if (params.status) query.set("status", params.status);
  const { data } = await api.get(`/clients?${query.toString()}`);
  return data.data ?? data;
}

async function createClient(values: ClientFormValues): Promise<Client> {
  const { data } = await api.post("/clients", values);
  return data.data ?? data;
}

// ── Columns ────────────────────────────────────────────

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-gray-100 text-gray-800",
  suspended: "bg-red-100 text-red-800",
};

function ActionsCell({ client }: { client: Client }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="rounded p-1 hover:bg-gray-100">
          <MoreHorizontal className="h-4 w-4" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <Link href={`/clients/${client.id}?mode=view`}>
            <Eye className="mr-2 h-4 w-4" /> View
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href={`/clients/${client.id}?mode=edit`}>
            <Pencil className="mr-2 h-4 w-4" /> Edit
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const columns: ColumnDef<Client, unknown>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        href={`/clients/${row.original.id}`}
        className="font-medium text-primary-600 hover:underline"
      >
        {row.original.name}
      </Link>
    ),
  },
  {
    accessorKey: "contact_person",
    header: "Contact",
    cell: ({ row }) => (
      <div>
        <div className="text-sm font-medium">{row.original.contact_person}</div>
        <div className="text-xs text-gray-500">{row.original.contact_phone}</div>
      </div>
    ),
  },
  { accessorKey: "city", header: "City" },
  {
    accessorKey: "rate_first_collection",
    header: "Rate (1st)",
    cell: ({ row }) => `₹${row.original.rate_first_collection}`,
  },
  {
    accessorKey: "rate_second_collection",
    header: "Rate (2nd)",
    cell: ({ row }) => `₹${row.original.rate_second_collection}`,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge className={statusColors[row.original.status] ?? ""}>
        {row.original.status}
      </Badge>
    ),
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => <ActionsCell client={row.original} />,
  },
];

// ── Page Component ─────────────────────────────────────

export default function ClientsPage() {
  const queryClient = useQueryClient();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filterCity, setFilterCity] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["clients", page, search, filterCity, filterStatus],
    queryFn: () =>
      fetchClients({ page, search, city: filterCity, status: filterStatus }),
    placeholderData: (prev) => prev,
  });

  const mutation = useMutation({
    mutationFn: createClient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setSheetOpen(false);
      form.reset();
    },
  });

  const form = useForm<ClientFormValues>({
    resolver: zodResolver(clientSchema),
    defaultValues: {
      name: "",
      contact_person: "",
      contact_phone: "",
      contact_email: "",
      city: "",
      address: "",
      rate_first_collection: 0,
      rate_second_collection: 0,
      rate_priority: 0,
      status: "active",
    },
  });

  const onSubmit = (values: ClientFormValues) => mutation.mutate(values);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage client organizations and their rate configurations.
          </p>
        </div>
        <button
          onClick={() => setSheetOpen(true)}
          className="inline-flex items-center gap-2 rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" /> Add Client
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            placeholder="Search clients..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-md border border-gray-300 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <input
          placeholder="Filter by city"
          value={filterCity}
          onChange={(e) => {
            setFilterCity(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
        <select
          value={filterStatus}
          onChange={(e) => {
            setFilterStatus(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : (
        <>
          <DataTable columns={columns} data={data?.items ?? []} />
          {/* Server pagination */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Page {data.page} of {data.total_pages} ({data.total} total)
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
                  disabled={page >= data.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Add Client Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>Add New Client</SheetTitle>
            <SheetDescription>
              Create a new client organization with rate configuration.
            </SheetDescription>
          </SheetHeader>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="mt-6 space-y-4"
            >
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Organization Name</FormLabel>
                    <FormControl>
                      <input
                        {...field}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="contact_person"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Contact Person</FormLabel>
                      <FormControl>
                        <input
                          {...field}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="contact_phone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Phone</FormLabel>
                      <FormControl>
                        <input
                          {...field}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="contact_email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <input
                        {...field}
                        type="email"
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="city"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>City</FormLabel>
                      <FormControl>
                        <input
                          {...field}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
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
                        <select
                          {...field}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        >
                          <option value="active">Active</option>
                          <option value="inactive">Inactive</option>
                          <option value="suspended">Suspended</option>
                        </select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Address</FormLabel>
                    <FormControl>
                      <textarea
                        {...field}
                        rows={2}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="rounded-md border bg-gray-50 p-4">
                <h3 className="mb-3 text-sm font-semibold text-gray-700">
                  Rate Configuration (₹)
                </h3>
                <div className="grid grid-cols-3 gap-3">
                  <FormField
                    control={form.control}
                    name="rate_first_collection"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>1st Collection</FormLabel>
                        <FormControl>
                          <input
                            {...field}
                            onChange={(e) => field.onChange(e.target.valueAsNumber || 0)}
                            type="number"
                            min={0}
                            step={0.01}
                            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="rate_second_collection"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>2nd Collection</FormLabel>
                        <FormControl>
                          <input
                            {...field}
                            onChange={(e) => field.onChange(e.target.valueAsNumber || 0)}
                            type="number"
                            min={0}
                            step={0.01}
                            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="rate_priority"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Priority</FormLabel>
                        <FormControl>
                          <input
                            {...field}
                            onChange={(e) => field.onChange(e.target.valueAsNumber || 0)}
                            type="number"
                            min={0}
                            step={0.01}
                            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              {mutation.isError && (
                <p className="text-sm text-red-600">
                  Failed to create client. Please try again.
                </p>
              )}

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setSheetOpen(false)}
                  className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={mutation.isPending}
                  className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {mutation.isPending ? "Creating..." : "Create Client"}
                </button>
              </div>
            </form>
          </Form>
        </SheetContent>
      </Sheet>
    </div>
  );
}
// cache bust 1771754953
