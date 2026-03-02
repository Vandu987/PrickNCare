"use client";

import React, { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowLeft,
  Save,
  UserPlus,
  Trash2,
  Phone,
  Mail,
  MapPin,
  Pencil,
} from "lucide-react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

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
  updated_at: string;
}

interface ClientUser {
  id: string;
  name: string;
  email: string;
  phone: string;
  role: string;
  status: string;
  created_at: string;
}

interface RateHistory {
  id: string;
  rate_first_collection: number;
  rate_second_collection: number;
  rate_priority: number;
  changed_by: string;
  changed_at: string;
  notes: string;
}

// ── Schemas ────────────────────────────────────────────

const clientEditSchema = z.object({
  name: z.string().min(1, "Name is required"),
  contact_person: z.string().min(1, "Contact person is required"),
  contact_phone: z.string().min(10, "Valid phone required"),
  contact_email: z.string().email("Valid email required"),
  city: z.string().min(1, "City is required"),
  address: z.string().min(1, "Address is required"),
  status: z.enum(["active", "inactive", "suspended"]),
});

const rateSchema = z.object({
  rate_first_collection: z.number().min(0),
  rate_second_collection: z.number().min(0),
  rate_priority: z.number().min(0),
  notes: z.string().optional(),
});

const addUserSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Valid email required"),
  phone: z.string().min(10, "Valid phone required"),
  role: z.string().min(1, "Role is required"),
});

type ClientEditValues = z.infer<typeof clientEditSchema>;
type RateValues = z.infer<typeof rateSchema>;
type AddUserValues = z.infer<typeof addUserSchema>;

// ── API ────────────────────────────────────────────────

async function fetchClient(id: string): Promise<Client> {
  const { data } = await api.get(`/clients/${id}`);
  return data.data ?? data;
}

async function updateClient(id: string, values: ClientEditValues): Promise<Client> {
  const { data } = await api.put(`/clients/${id}`, values);
  return data.data ?? data;
}

async function updateRates(id: string, values: RateValues): Promise<Client> {
  const { data } = await api.put(`/clients/${id}/rates`, values);
  return data.data ?? data;
}

async function fetchClientUsers(id: string): Promise<ClientUser[]> {
  const { data } = await api.get(`/clients/${id}/users`);
  return data.items ?? data.data ?? data;
}

async function addClientUser(id: string, values: AddUserValues): Promise<ClientUser> {
  const { data } = await api.post(`/clients/${id}/users`, values);
  return data.data ?? data;
}

async function removeClientUser(clientId: string, userId: string): Promise<void> {
  await api.delete(`/clients/${clientId}/users/${userId}`);
}

async function fetchRateHistory(id: string): Promise<RateHistory[]> {
  const { data } = await api.get(`/clients/${id}/rate-history`);
  return data.data ?? data;
}

// ── Status colors ──────────────────────────────────────

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-gray-100 text-gray-800",
  suspended: "bg-red-100 text-red-800",
};

// ── Tab Components ─────────────────────────────────────

function InfoTab({ client, readOnly }: { client: Client; readOnly?: boolean }) {
  const queryClient = useQueryClient();
  const form = useForm<ClientEditValues>({
    resolver: zodResolver(clientEditSchema),
    values: {
      name: client.name,
      contact_person: client.contact_person,
      contact_phone: client.contact_phone,
      contact_email: client.contact_email,
      city: client.city,
      address: client.address,
      status: client.status,
    },
  });

  const mutation = useMutation({
    mutationFn: (values: ClientEditValues) => updateClient(client.id, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client", client.id] });
    },
  });

  if (readOnly) {
    const fields = [
      { label: "Organization Name", value: client.name },
      { label: "Contact Person", value: client.contact_person },
      { label: "Phone", value: client.contact_phone },
      { label: "Email", value: client.contact_email },
      { label: "City", value: client.city },
      { label: "Address", value: client.address },
      { label: "Status", value: client.status },
      { label: "Created", value: client.created_at ? new Date(client.created_at).toLocaleDateString("en-IN") : "—" },
    ];
    return (
      <div className="rounded-lg border bg-white p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {fields.map((f) => (
            <div key={f.label}>
              <p className="text-xs font-medium text-gray-500">{f.label}</p>
              <p className="mt-1 text-sm text-gray-900">{f.value || "—"}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 rounded-md border bg-gray-50 p-4">
          <h3 className="mb-3 text-sm font-semibold text-gray-700">Rate Configuration</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs font-medium text-gray-500">1st Collection</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">₹{client.rate_first_collection}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500">2nd Collection</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">₹{client.rate_second_collection}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500">Priority</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">₹{client.rate_priority}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
        className="space-y-4"
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

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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

        {mutation.isSuccess && (
          <p className="text-sm text-green-600">Client updated successfully.</p>
        )}
        {mutation.isError && (
          <p className="text-sm text-red-600">Failed to update client.</p>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="inline-flex items-center gap-2 rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {mutation.isPending ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </form>
    </Form>
  );
}

function RatesTab({ client }: { client: Client }) {
  const queryClient = useQueryClient();
  const form = useForm<RateValues>({
    resolver: zodResolver(rateSchema),
    values: {
      rate_first_collection: client.rate_first_collection,
      rate_second_collection: client.rate_second_collection,
      rate_priority: client.rate_priority,
      notes: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (values: RateValues) => updateRates(client.id, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client", client.id] });
      queryClient.invalidateQueries({ queryKey: ["rate-history", client.id] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Current rates */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { label: "1st Collection", value: client.rate_first_collection },
          { label: "2nd Collection", value: client.rate_second_collection },
          { label: "Priority", value: client.rate_priority },
        ].map((r) => (
          <div
            key={r.label}
            className="rounded-lg border bg-white p-4 text-center shadow-sm"
          >
            <p className="text-sm text-gray-500">{r.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">₹{r.value}</p>
          </div>
        ))}
      </div>

      {/* Update form */}
      <div className="rounded-lg border bg-gray-50 p-6">
        <h3 className="mb-4 text-sm font-semibold text-gray-700">
          Update Rates
        </h3>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
            className="space-y-4"
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <FormField
                control={form.control}
                name="rate_first_collection"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>1st Collection (₹)</FormLabel>
                    <FormControl>
                      <input
                        {...field}
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
                    <FormLabel>2nd Collection (₹)</FormLabel>
                    <FormControl>
                      <input
                        {...field}
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
                    <FormLabel>Priority (₹)</FormLabel>
                    <FormControl>
                      <input
                        {...field}
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

            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes (optional)</FormLabel>
                  <FormControl>
                    <input
                      {...field}
                      placeholder="Reason for rate change..."
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {mutation.isSuccess && (
              <p className="text-sm text-green-600">Rates updated successfully.</p>
            )}
            {mutation.isError && (
              <p className="text-sm text-red-600">Failed to update rates.</p>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={mutation.isPending}
                className="inline-flex items-center gap-2 rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                <Save className="h-4 w-4" />
                {mutation.isPending ? "Updating..." : "Update Rates"}
              </button>
            </div>
          </form>
        </Form>
      </div>

      {/* Rate History */}
      <RateHistoryTable clientId={client.id} />
    </div>
  );
}

function RateHistoryTable({ clientId }: { clientId: string }) {
  const { data: history, isLoading } = useQuery({
    queryKey: ["rate-history", clientId],
    queryFn: () => fetchRateHistory(clientId),
  });

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Rate History</h3>
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : !history?.length ? (
        <p className="py-4 text-center text-sm text-gray-500">
          No rate changes recorded.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left">
                <th className="px-4 py-3 font-medium text-gray-500">Date</th>
                <th className="px-4 py-3 font-medium text-gray-500">1st</th>
                <th className="px-4 py-3 font-medium text-gray-500">2nd</th>
                <th className="px-4 py-3 font-medium text-gray-500">Priority</th>
                <th className="px-4 py-3 font-medium text-gray-500">Changed By</th>
                <th className="px-4 py-3 font-medium text-gray-500">Notes</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3">
                    {new Date(h.changed_at).toLocaleDateString("en-IN")}
                  </td>
                  <td className="px-4 py-3">₹{h.rate_first_collection}</td>
                  <td className="px-4 py-3">₹{h.rate_second_collection}</td>
                  <td className="px-4 py-3">₹{h.rate_priority}</td>
                  <td className="px-4 py-3">{h.changed_by}</td>
                  <td className="px-4 py-3 text-gray-500">{h.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function UsersTab({ clientId }: { clientId: string }) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: users, isLoading } = useQuery({
    queryKey: ["client-users", clientId],
    queryFn: () => fetchClientUsers(clientId),
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => removeClientUser(clientId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client-users", clientId] });
    },
  });

  const form = useForm<AddUserValues>({
    resolver: zodResolver(addUserSchema),
    defaultValues: { name: "", email: "", phone: "", role: "client_user" },
  });

  const addMutation = useMutation({
    mutationFn: (values: AddUserValues) => addClientUser(clientId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client-users", clientId] });
      setDialogOpen(false);
      form.reset();
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Client Users</h3>
        <button
          onClick={() => setDialogOpen(true)}
          className="inline-flex items-center gap-2 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700"
        >
          <UserPlus className="h-4 w-4" /> Add User
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : !users?.length ? (
        <p className="py-4 text-center text-sm text-gray-500">
          No users assigned to this client.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left">
                <th className="px-4 py-3 font-medium text-gray-500">Name</th>
                <th className="px-4 py-3 font-medium text-gray-500">Email</th>
                <th className="px-4 py-3 font-medium text-gray-500">Phone</th>
                <th className="px-4 py-3 font-medium text-gray-500">Role</th>
                <th className="px-4 py-3 font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 font-medium text-gray-500"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{u.name}</td>
                  <td className="px-4 py-3">{u.email}</td>
                  <td className="px-4 py-3">{u.phone}</td>
                  <td className="px-4 py-3">
                    <Badge variant="secondary">{u.role}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      className={
                        u.status === "active"
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-800"
                      }
                    >
                      {u.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => {
                        if (confirm("Remove this user from the client?"))
                          removeMutation.mutate(u.id);
                      }}
                      className="rounded p-1 text-red-500 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add User Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add User to Client</DialogTitle>
            <DialogDescription>
              Add a new user who can access this client&apos;s portal.
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit((v) => addMutation.mutate(v))}
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
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Role</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        <option value="client_admin">Client Admin</option>
                        <option value="client_user">Client User</option>
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {addMutation.isError && (
                <p className="text-sm text-red-600">Failed to add user.</p>
              )}

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setDialogOpen(false)}
                  className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addMutation.isPending}
                  className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {addMutation.isPending ? "Adding..." : "Add User"}
                </button>
              </div>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────

const tabs = [
  { key: "info", label: "Info" },
  { key: "rates", label: "Rates" },
  { key: "users", label: "Users" },
] as const;

type TabKey = (typeof tabs)[number]["key"];

export default function ClientDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const id = params.id as string;
  const isViewMode = searchParams.get("mode") !== "edit";
  const initialTab = (searchParams.get("tab") as TabKey) || "info";
  const [activeTab, setActiveTab] = useState<TabKey>(
    tabs.some((t) => t.key === initialTab) ? initialTab : "info"
  );

  const { data: client, isLoading } = useQuery({
    queryKey: ["client", id],
    queryFn: () => fetchClient(id),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!client) {
    return (
      <div className="py-24 text-center">
        <p className="text-gray-500">Client not found.</p>
        <Link
          href="/clients"
          className="mt-2 inline-block text-sm text-primary-600 hover:underline"
        >
          ← Back to clients
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/clients"
            className="rounded-md p-1 hover:bg-gray-100"
          >
            <ArrowLeft className="h-5 w-5 text-gray-500" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-gray-900">
                {client.name}
              </h1>
              <Badge className={statusColors[client.status] ?? ""}>
                {client.status}
              </Badge>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-4 text-sm text-gray-500">
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" /> {client.city}
              </span>
              <span className="inline-flex items-center gap-1">
                <Phone className="h-3.5 w-3.5" /> {client.contact_phone}
              </span>
              <span className="inline-flex items-center gap-1">
                <Mail className="h-3.5 w-3.5" /> {client.contact_email}
              </span>
            </div>
          </div>
        </div>
        {isViewMode && (
          <Link
            href={`/clients/${id}?mode=edit`}
            className="inline-flex items-center gap-2 rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            <Pencil className="h-4 w-4" /> Edit
          </Link>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="-mb-px flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`border-b-2 pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-primary-600 text-primary-600"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "info" && <InfoTab client={client} readOnly={isViewMode} />}
        {activeTab === "rates" && <RatesTab client={client} />}
        {activeTab === "users" && <UsersTab clientId={client.id} />}
      </div>
    </div>
  );
}
