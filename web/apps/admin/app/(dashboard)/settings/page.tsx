"use client";

import React, { useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Save, Eye, EyeOff } from "lucide-react";
import api from "@/lib/api";

/* ── Profile Settings ─────────────────────────── */

function ProfileSettings() {
  const { user } = useAuth();
  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleProfileSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.patch("/users/me", { name, email });
      setMessage({ type: "success", text: "Profile updated successfully." });
    } catch {
      setMessage({ type: "error", text: "Failed to update profile." });
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async () => {
    if (newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "Passwords do not match." });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await api.patch("/users/me/password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage({ type: "success", text: "Password changed successfully." });
    } catch {
      setMessage({ type: "error", text: "Failed to change password." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {message && (
        <div
          className={`rounded-md p-3 text-sm ${
            message.type === "success"
              ? "bg-green-50 text-green-800"
              : "bg-red-50 text-red-800"
          }`}
        >
          {message.text}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
          <CardDescription>Update your name and email address.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <Button onClick={handleProfileSave} disabled={saving}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving…" : "Save Changes"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change Password</CardTitle>
          <CardDescription>Ensure your account uses a strong password.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Current Password</label>
            <div className="relative mt-1">
              <input
                type={showPassword ? "text" : "password"}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Confirm New Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <Button onClick={handlePasswordChange} disabled={saving}>
            {saving ? "Updating…" : "Update Password"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Notification Preferences ─────────────────── */

interface NotificationPref {
  key: string;
  label: string;
  email: boolean;
  sms: boolean;
  push: boolean;
}

const defaultPrefs: NotificationPref[] = [
  { key: "booking_created", label: "New Booking", email: true, sms: true, push: true },
  { key: "booking_completed", label: "Booking Completed", email: true, sms: false, push: true },
  { key: "payment_received", label: "Payment Received", email: true, sms: false, push: false },
  { key: "report_ready", label: "Report Ready", email: true, sms: true, push: true },
  { key: "phlebotomist_assigned", label: "Phlebotomist Assigned", email: false, sms: false, push: true },
];

function NotificationSettings() {
  const [prefs, setPrefs] = useState<NotificationPref[]>(defaultPrefs);
  const [saving, setSaving] = useState(false);

  const toggle = (key: string, channel: "email" | "sms" | "push") => {
    setPrefs((prev) =>
      prev.map((p) => (p.key === key ? { ...p, [channel]: !p[channel] } : p))
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch("/users/me/notifications", { preferences: prefs });
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notification Preferences</CardTitle>
        <CardDescription>Choose how you want to be notified.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="pb-2 pr-4 font-medium">Event</th>
                <th className="pb-2 px-4 font-medium text-center">Email</th>
                <th className="pb-2 px-4 font-medium text-center">SMS</th>
                <th className="pb-2 px-4 font-medium text-center">Push</th>
              </tr>
            </thead>
            <tbody>
              {prefs.map((p) => (
                <tr key={p.key} className="border-b last:border-0">
                  <td className="py-3 pr-4 text-gray-700">{p.label}</td>
                  {(["email", "sms", "push"] as const).map((ch) => (
                    <td key={ch} className="py-3 px-4 text-center">
                      <button
                        type="button"
                        onClick={() => toggle(p.key, ch)}
                        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                          p[ch] ? "bg-primary-600" : "bg-gray-200"
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow ring-0 transition-transform ${
                            p[ch] ? "translate-x-4" : "translate-x-0"
                          }`}
                        />
                      </button>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4">
          <Button onClick={handleSave} disabled={saving}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving…" : "Save Preferences"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── System Settings (SUPER_ADMIN only) ───────── */

function SystemSettings() {
  const [companyName, setCompanyName] = useState("PricknCare Diagnostics");
  const [companyEmail, setCompanyEmail] = useState("info@prickncare.com");
  const [companyPhone, setCompanyPhone] = useState("+91 9876543210");
  const [defaultRate, setDefaultRate] = useState("350");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch("/settings/system", {
        company_name: companyName,
        company_email: companyEmail,
        company_phone: companyPhone,
        default_rate: Number(defaultRate),
      });
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Company Information</CardTitle>
          <CardDescription>Manage your company details visible across the platform.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Company Name</label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Contact Email</label>
            <input
              type="email"
              value={companyEmail}
              onChange={(e) => setCompanyEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Contact Phone</label>
            <input
              type="text"
              value={companyPhone}
              onChange={(e) => setCompanyPhone(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Default Rates</CardTitle>
          <CardDescription>Set default pricing for services.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Default Collection Rate (₹)
            </label>
            <input
              type="number"
              value={defaultRate}
              onChange={(e) => setDefaultRate(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notification Templates</CardTitle>
          <CardDescription>Customize notification messages sent to users.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Booking Confirmation Template
            </label>
            <textarea
              rows={3}
              defaultValue="Dear {{name}}, your booking #{{booking_id}} has been confirmed for {{date}} at {{time}}."
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Report Ready Template
            </label>
            <textarea
              rows={3}
              defaultValue="Dear {{name}}, your lab report for booking #{{booking_id}} is ready. Download it from your dashboard."
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <Button onClick={handleSave} disabled={saving}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving…" : "Save System Settings"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Main Settings Page ───────────────────────── */

export default function SettingsPage() {
  const { hasRole } = useAuth();
  const isSuperAdmin = hasRole("super_admin");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your account settings and preferences.
        </p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          {isSuperAdmin && <TabsTrigger value="system">System</TabsTrigger>}
        </TabsList>
        <TabsContent value="profile">
          <ProfileSettings />
        </TabsContent>
        <TabsContent value="notifications">
          <NotificationSettings />
        </TabsContent>
        {isSuperAdmin && (
          <TabsContent value="system">
            <SystemSettings />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
