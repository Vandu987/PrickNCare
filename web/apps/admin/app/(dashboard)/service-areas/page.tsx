"use client";

import React, { useState, useMemo, useRef } from "react";
import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ChevronRight,
  ChevronDown,
  Plus,
  Pencil,
  Trash2,
  Search,
  Upload,
  MapPin,
  Building2,
  Map,
  Hash,
  Home,
  ShieldAlert,
  ShieldCheck,
  X,
} from "lucide-react";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";

// ── Types ──────────────────────────────────────────────

interface City {
  id: string;
  name: string;
  state: string;
  is_serviceable: boolean;
  created_at: string;
}

interface Zone {
  id: string;
  name: string;
  city_id: string;
  city_name: string;
  is_active: boolean;
  pincode_count: number;
  created_at: string;
}

interface PincodeItem {
  id: string;
  pincode: string;
  zone_id: string;
  zone_name: string;
  created_at: string;
}

interface Locality {
  id: string;
  name: string;
  pincode_id: string;
  pincode: string;
  zone_name: string;
}

interface NSARecord {
  id: string;
  pincode: string;
  reason: string;
  is_active: boolean;
  marked_at: string;
}

interface ListResponse<T> {
  items: T[];
  total: number;
}

// ── API hooks ──────────────────────────────────────────

function useCities() {
  return useQuery<ListResponse<City>>({
    queryKey: ["cities"],
    queryFn: () => api.get("/cities?limit=200").then((r) => r.data),
  });
}

function useZones(cityId?: string) {
  return useQuery<ListResponse<Zone>>({
    queryKey: ["zones", cityId],
    queryFn: () =>
      api
        .get(`/zones?limit=200${cityId ? `&city_id=${cityId}` : ""}`)
        .then((r) => r.data),
    enabled: cityId !== undefined,
  });
}

function usePincodes(zoneId?: string) {
  return useQuery<ListResponse<PincodeItem>>({
    queryKey: ["pincodes", zoneId],
    queryFn: () =>
      api
        .get(`/pincodes?limit=200${zoneId ? `&zone_id=${zoneId}` : ""}`)
        .then((r) => r.data),
    enabled: zoneId !== undefined,
  });
}

function useLocalities(pincodeId?: string) {
  return useQuery<ListResponse<Locality>>({
    queryKey: ["localities", pincodeId],
    queryFn: () =>
      api
        .get(
          `/localities?limit=200${pincodeId ? `&pincode_id=${pincodeId}` : ""}`
        )
        .then((r) => r.data),
    enabled: pincodeId !== undefined,
  });
}

function useNSAList() {
  return useQuery<ListResponse<NSARecord>>({
    queryKey: ["nsa"],
    queryFn: () => api.get("/nsa/list?limit=200").then((r) => r.data),
  });
}

// ── Reusable small components ──────────────────────────

function ToggleSwitch({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        onChange(!checked);
      }}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors",
        checked ? "bg-green-500" : "bg-gray-300",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      <span
        className={cn(
          "pointer-events-none block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-transform",
          checked ? "translate-x-4" : "translate-x-0"
        )}
      />
    </button>
  );
}

function IconBtn({
  onClick,
  children,
  title,
  variant = "ghost",
}: {
  onClick: (e: React.MouseEvent) => void;
  children: React.ReactNode;
  title?: string;
  variant?: "ghost" | "danger";
}) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick(e);
      }}
      title={title}
      className={cn(
        "p-1 rounded hover:bg-gray-100 transition-colors",
        variant === "danger" && "hover:bg-red-50 hover:text-red-600"
      )}
    >
      {children}
    </button>
  );
}

// ── Locality row ───────────────────────────────────────

function LocalityRow({
  locality,
  onEdit,
  onDelete,
}: {
  locality: Locality;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-center gap-2 py-1.5 pl-20 pr-4 hover:bg-gray-50 group">
      <Home className="h-3.5 w-3.5 text-gray-400 shrink-0" />
      <span className="text-sm text-gray-700 flex-1">{locality.name}</span>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <IconBtn onClick={onEdit} title="Edit">
          <Pencil className="h-3.5 w-3.5 text-gray-500" />
        </IconBtn>
        <IconBtn onClick={onDelete} title="Delete" variant="danger">
          <Trash2 className="h-3.5 w-3.5" />
        </IconBtn>
      </div>
    </div>
  );
}

// ── Pincode row with expandable localities ─────────────

function PincodeRow({
  pincode,
  nsaSet,
  onMarkNSA,
  onUnmarkNSA,
  onDelete,
  onAddLocality,
  onEditLocality,
  onDeleteLocality,
}: {
  pincode: PincodeItem;
  nsaSet: Set<string>;
  onMarkNSA: (pincode: string) => void;
  onUnmarkNSA: (pincode: string) => void;
  onDelete: () => void;
  onAddLocality: (pincodeId: string) => void;
  onEditLocality: (loc: Locality) => void;
  onDeleteLocality: (loc: Locality) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const localities = useLocalities(expanded ? pincode.id : undefined);
  const isNSA = nsaSet.has(pincode.pincode);

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1.5 pl-14 pr-4 hover:bg-gray-50 cursor-pointer group"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
        )}
        <Hash className="h-3.5 w-3.5 text-gray-400 shrink-0" />
        <span className="text-sm font-mono text-gray-700">{pincode.pincode}</span>
        {isNSA && (
          <Badge variant="destructive" className="text-xs py-0 px-1.5">
            NSA
          </Badge>
        )}
        <div className="flex-1" />
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {isNSA ? (
            <IconBtn
              onClick={() => onUnmarkNSA(pincode.pincode)}
              title="Mark as serviceable"
            >
              <ShieldCheck className="h-3.5 w-3.5 text-green-600" />
            </IconBtn>
          ) : (
            <IconBtn
              onClick={() => onMarkNSA(pincode.pincode)}
              title="Mark as non-serviceable"
            >
              <ShieldAlert className="h-3.5 w-3.5 text-orange-500" />
            </IconBtn>
          )}
          <IconBtn
            onClick={() => onAddLocality(pincode.id)}
            title="Add locality"
          >
            <Plus className="h-3.5 w-3.5 text-gray-500" />
          </IconBtn>
          <IconBtn onClick={onDelete} title="Delete pincode" variant="danger">
            <Trash2 className="h-3.5 w-3.5" />
          </IconBtn>
        </div>
      </div>
      {expanded && (
        <div>
          {localities.isLoading && (
            <div className="pl-24 py-1 text-xs text-gray-400">Loading…</div>
          )}
          {localities.data?.items.map((loc) => (
            <LocalityRow
              key={loc.id}
              locality={loc}
              onEdit={() => onEditLocality(loc)}
              onDelete={() => onDeleteLocality(loc)}
            />
          ))}
          {localities.data && localities.data.items.length === 0 && (
            <div className="pl-24 py-1 text-xs text-gray-400">
              No localities
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Zone row with expandable pincodes ──────────────────

function ZoneRow({
  zone,
  nsaSet,
  onToggleActive,
  onEdit,
  onDelete,
  onAddPincode,
  onDeletePincode,
  onMarkNSA,
  onUnmarkNSA,
  onAddLocality,
  onEditLocality,
  onDeleteLocality,
}: {
  zone: Zone;
  nsaSet: Set<string>;
  onToggleActive: (zone: Zone) => void;
  onEdit: (zone: Zone) => void;
  onDelete: (zone: Zone) => void;
  onAddPincode: (zoneId: string) => void;
  onDeletePincode: (p: PincodeItem) => void;
  onMarkNSA: (pincode: string) => void;
  onUnmarkNSA: (pincode: string) => void;
  onAddLocality: (pincodeId: string) => void;
  onEditLocality: (loc: Locality) => void;
  onDeleteLocality: (loc: Locality) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const pincodes = usePincodes(expanded ? zone.id : undefined);

  return (
    <div>
      <div
        className="flex items-center gap-2 py-2 pl-8 pr-4 hover:bg-gray-50 cursor-pointer group"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
        )}
        <Map className="h-4 w-4 text-blue-500 shrink-0" />
        <span className="text-sm font-medium text-gray-800">{zone.name}</span>
        <Badge
          variant={zone.is_active ? "default" : "secondary"}
          className="text-xs py-0 px-1.5"
        >
          {zone.is_active ? "Active" : "Inactive"}
        </Badge>
        <span className="text-xs text-gray-400">
          {zone.pincode_count} pincodes
        </span>
        <div className="flex-1" />
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <ToggleSwitch
            checked={zone.is_active}
            onChange={() => onToggleActive(zone)}
          />
          <IconBtn onClick={() => onAddPincode(zone.id)} title="Add pincode">
            <Plus className="h-3.5 w-3.5 text-gray-500" />
          </IconBtn>
          <IconBtn onClick={() => onEdit(zone)} title="Edit zone">
            <Pencil className="h-3.5 w-3.5 text-gray-500" />
          </IconBtn>
          <IconBtn
            onClick={() => onDelete(zone)}
            title="Delete zone"
            variant="danger"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </IconBtn>
        </div>
      </div>
      {expanded && (
        <div>
          {pincodes.isLoading && (
            <div className="pl-20 py-1 text-xs text-gray-400">Loading…</div>
          )}
          {pincodes.data?.items.map((p) => (
            <PincodeRow
              key={p.id}
              pincode={p}
              nsaSet={nsaSet}
              onMarkNSA={onMarkNSA}
              onUnmarkNSA={onUnmarkNSA}
              onDelete={() => onDeletePincode(p)}
              onAddLocality={onAddLocality}
              onEditLocality={onEditLocality}
              onDeleteLocality={onDeleteLocality}
            />
          ))}
          {pincodes.data && pincodes.data.items.length === 0 && (
            <div className="pl-20 py-1 text-xs text-gray-400">
              No pincodes
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── City row with expandable zones ─────────────────────

function CityRow({
  city,
  nsaSet,
  onToggleServiceable,
  onEdit,
  onDelete,
  onAddZone,
  onEditZone,
  onDeleteZone,
  onToggleZoneActive,
  onAddPincode,
  onDeletePincode,
  onMarkNSA,
  onUnmarkNSA,
  onAddLocality,
  onEditLocality,
  onDeleteLocality,
}: {
  city: City;
  nsaSet: Set<string>;
  onToggleServiceable: (city: City) => void;
  onEdit: (city: City) => void;
  onDelete: (city: City) => void;
  onAddZone: (cityId: string) => void;
  onEditZone: (zone: Zone) => void;
  onDeleteZone: (zone: Zone) => void;
  onToggleZoneActive: (zone: Zone) => void;
  onAddPincode: (zoneId: string) => void;
  onDeletePincode: (p: PincodeItem) => void;
  onMarkNSA: (pincode: string) => void;
  onUnmarkNSA: (pincode: string) => void;
  onAddLocality: (pincodeId: string) => void;
  onEditLocality: (loc: Locality) => void;
  onDeleteLocality: (loc: Locality) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const zones = useZones(expanded ? city.id : undefined);

  return (
    <div className="border-b last:border-b-0">
      <div
        className="flex items-center gap-2 py-3 px-4 hover:bg-gray-50 cursor-pointer group"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-5 w-5 text-gray-500 shrink-0" />
        ) : (
          <ChevronRight className="h-5 w-5 text-gray-500 shrink-0" />
        )}
        <Building2 className="h-5 w-5 text-indigo-500 shrink-0" />
        <span className="font-semibold text-gray-900">{city.name}</span>
        {city.state && (
          <span className="text-xs text-gray-400">{city.state}</span>
        )}
        <Badge
          variant={city.is_serviceable ? "default" : "secondary"}
          className="text-xs py-0 px-1.5"
        >
          {city.is_serviceable ? "Serviceable" : "Not Serviceable"}
        </Badge>
        <div className="flex-1" />
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <ToggleSwitch
            checked={city.is_serviceable}
            onChange={() => onToggleServiceable(city)}
          />
          <IconBtn onClick={() => onAddZone(city.id)} title="Add zone">
            <Plus className="h-4 w-4 text-gray-500" />
          </IconBtn>
          <IconBtn onClick={() => onEdit(city)} title="Edit city">
            <Pencil className="h-4 w-4 text-gray-500" />
          </IconBtn>
          <IconBtn
            onClick={() => onDelete(city)}
            title="Delete city"
            variant="danger"
          >
            <Trash2 className="h-4 w-4" />
          </IconBtn>
        </div>
      </div>
      {expanded && (
        <div className="bg-gray-50/50">
          {zones.isLoading && (
            <div className="pl-14 py-2 text-sm text-gray-400">Loading…</div>
          )}
          {zones.data?.items.map((z) => (
            <ZoneRow
              key={z.id}
              zone={z}
              nsaSet={nsaSet}
              onToggleActive={onToggleZoneActive}
              onEdit={onEditZone}
              onDelete={onDeleteZone}
              onAddPincode={onAddPincode}
              onDeletePincode={onDeletePincode}
              onMarkNSA={onMarkNSA}
              onUnmarkNSA={onUnmarkNSA}
              onAddLocality={onAddLocality}
              onEditLocality={onEditLocality}
              onDeleteLocality={onDeleteLocality}
            />
          ))}
          {zones.data && zones.data.items.length === 0 && (
            <div className="pl-14 py-2 text-sm text-gray-400">No zones</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Dialog forms ───────────────────────────────────────

function CityDialog({
  open,
  onClose,
  city,
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  city?: City;
  onSubmit: (data: { name: string; state: string }) => void;
  loading: boolean;
}) {
  const [name, setName] = useState(city?.name ?? "");
  const [state, setState] = useState(city?.state ?? "");

  React.useEffect(() => {
    if (open) {
      setName(city?.name ?? "");
      setState(city?.state ?? "");
    }
  }, [open, city]);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{city ? "Edit City" : "Add City"}</DialogTitle>
          <DialogDescription>
            {city ? "Update city details." : "Add a new city to service areas."}
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ name: name.trim(), state: state.trim() });
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              City Name *
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. Mumbai"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              State
            </label>
            <input
              value={state}
              onChange={(e) => setState(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. Maharashtra"
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <button
                type="button"
                className="px-4 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </button>
            </DialogClose>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? "Saving…" : "Save"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ZoneDialog({
  open,
  onClose,
  zone,
  cityId,
  cities,
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  zone?: Zone;
  cityId?: string;
  cities: City[];
  onSubmit: (data: { name: string; city_id: string }) => void;
  loading: boolean;
}) {
  const [name, setName] = useState(zone?.name ?? "");
  const [selectedCityId, setSelectedCityId] = useState(
    zone?.city_id ?? cityId ?? ""
  );

  React.useEffect(() => {
    if (open) {
      setName(zone?.name ?? "");
      setSelectedCityId(zone?.city_id ?? cityId ?? cities[0]?.id ?? "");
    }
  }, [open, zone, cityId, cities]);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{zone ? "Edit Zone" : "Add Zone"}</DialogTitle>
          <DialogDescription>
            {zone ? "Update zone details." : "Add a new zone."}
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ name: name.trim(), city_id: selectedCityId });
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Zone Name *
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. South Mumbai"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              City *
            </label>
            <select
              value={selectedCityId}
              onChange={(e) => setSelectedCityId(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="" disabled>
                Select a city
              </option>
              {cities.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <button
                type="button"
                className="px-4 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </button>
            </DialogClose>
            <button
              type="submit"
              disabled={loading || !name.trim() || !selectedCityId}
              className="px-4 py-2 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? "Saving…" : "Save"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function PincodeDialog({
  open,
  onClose,
  zoneId,
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  zoneId: string;
  onSubmit: (data: { pincode: string; zone_id: string }) => void;
  loading: boolean;
}) {
  const [pincode, setPincode] = useState("");

  React.useEffect(() => {
    if (open) setPincode("");
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Pincode</DialogTitle>
          <DialogDescription>Add a 6-digit pincode to this zone.</DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ pincode: pincode.trim(), zone_id: zoneId });
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Pincode *
            </label>
            <input
              value={pincode}
              onChange={(e) => {
                const v = e.target.value.replace(/\D/g, "").slice(0, 6);
                setPincode(v);
              }}
              required
              pattern="\d{6}"
              maxLength={6}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. 400001"
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <button
                type="button"
                className="px-4 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </button>
            </DialogClose>
            <button
              type="submit"
              disabled={loading || pincode.length !== 6}
              className="px-4 py-2 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? "Adding…" : "Add"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function LocalityDialog({
  open,
  onClose,
  locality,
  pincodeId,
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  locality?: Locality;
  pincodeId: string;
  onSubmit: (data: { name: string; pincode_id: string; id?: string }) => void;
  loading: boolean;
}) {
  const [name, setName] = useState(locality?.name ?? "");

  React.useEffect(() => {
    if (open) setName(locality?.name ?? "");
  }, [open, locality]);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {locality ? "Edit Locality" : "Add Locality"}
          </DialogTitle>
          <DialogDescription>
            {locality ? "Update locality name." : "Add a new locality."}
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({
              name: name.trim(),
              pincode_id: pincodeId,
              id: locality?.id,
            });
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Locality Name *
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. Colaba"
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <button
                type="button"
                className="px-4 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </button>
            </DialogClose>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? "Saving…" : "Save"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function NSADialog({
  open,
  onClose,
  onSubmit,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { pincode: string; reason: string }) => void;
  loading: boolean;
}) {
  const [pincode, setPincode] = useState("");
  const [reason, setReason] = useState("");

  React.useEffect(() => {
    if (open) {
      setPincode("");
      setReason("");
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Mark Pincode as Non-Serviceable</DialogTitle>
          <DialogDescription>
            This pincode will be blocked from new orders.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ pincode: pincode.trim(), reason: reason.trim() });
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Pincode *
            </label>
            <input
              value={pincode}
              onChange={(e) =>
                setPincode(e.target.value.replace(/\D/g, "").slice(0, 6))
              }
              required
              pattern="\d{6}"
              maxLength={6}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="400001"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reason
            </label>
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. No phlebotomist available"
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <button
                type="button"
                className="px-4 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </button>
            </DialogClose>
            <button
              type="submit"
              disabled={loading || pincode.length !== 6}
              className="px-4 py-2 text-sm rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
            >
              {loading ? "Marking…" : "Mark NSA"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function CSVImportDialog({
  open,
  onClose,
  onUpload,
  loading,
  result,
}: {
  open: boolean;
  onClose: () => void;
  onUpload: (file: File) => void;
  loading: boolean;
  result?: { total_rows: number; created: number; errors: number; error_details: string[] };
}) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Import from CSV</DialogTitle>
          <DialogDescription>
            Upload a CSV with columns: <code className="text-xs bg-gray-100 px-1 rounded">city, zone, pincode, locality</code> (locality optional).
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-600 hover:file:bg-indigo-100"
          />
          {result && (
            <div className="rounded-md bg-gray-50 p-3 text-sm space-y-1">
              <p>
                <strong>Total rows:</strong> {result.total_rows} |{" "}
                <strong>Created:</strong> {result.created} |{" "}
                <strong>Errors:</strong> {result.errors}
              </p>
              {result.error_details.length > 0 && (
                <div className="max-h-32 overflow-auto text-xs text-red-600 space-y-0.5">
                  {result.error_details.map((e, i) => (
                    <p key={i}>{e}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <button
              type="button"
              className="px-4 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
            >
              Close
            </button>
          </DialogClose>
          <button
            type="button"
            disabled={loading}
            onClick={() => {
              const file = fileRef.current?.files?.[0];
              if (file) onUpload(file);
            }}
            className="px-4 py-2 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "Importing…" : "Import"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  loading: boolean;
}) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <button
              type="button"
              className="px-4 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
            >
              Cancel
            </button>
          </DialogClose>
          <button
            type="button"
            disabled={loading}
            onClick={onConfirm}
            className="px-4 py-2 text-sm rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? "Deleting…" : "Delete"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Main page ──────────────────────────────────────────

export default function ServiceAreasPage() {
  const qc = useQueryClient();
  const cities = useCities();
  const nsaList = useNSAList();

  const [search, setSearch] = useState("");

  // Dialog states
  const [cityDialog, setCityDialog] = useState<{
    open: boolean;
    city?: City;
  }>({ open: false });
  const [zoneDialog, setZoneDialog] = useState<{
    open: boolean;
    zone?: Zone;
    cityId?: string;
  }>({ open: false });
  const [pincodeDialog, setPincodeDialog] = useState<{
    open: boolean;
    zoneId: string;
  }>({ open: false, zoneId: "" });
  const [localityDialog, setLocalityDialog] = useState<{
    open: boolean;
    locality?: Locality;
    pincodeId: string;
  }>({ open: false, pincodeId: "" });
  const [nsaDialog, setNsaDialog] = useState(false);
  const [csvDialog, setCsvDialog] = useState(false);
  const [csvResult, setCsvResult] = useState<{
    total_rows: number;
    created: number;
    errors: number;
    error_details: string[];
  }>();
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    title: string;
    description: string;
    onConfirm: () => void;
  }>({ open: false, title: "", description: "", onConfirm: () => {} });

  // NSA set for quick lookups
  const nsaSet = useMemo(() => {
    const s = new Set<string>();
    nsaList.data?.items.forEach((r) => s.add(r.pincode));
    return s;
  }, [nsaList.data]);

  // Filtered cities
  const filteredCities = useMemo(() => {
    if (!cities.data?.items) return [];
    if (!search.trim()) return cities.data.items;
    const q = search.toLowerCase();
    return cities.data.items.filter((c) =>
      c.name.toLowerCase().includes(q) ||
      c.state?.toLowerCase().includes(q)
    );
  }, [cities.data, search]);

  // ── Mutations ──────────────────────────────────────────

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["cities"] });
    qc.invalidateQueries({ queryKey: ["zones"] });
    qc.invalidateQueries({ queryKey: ["pincodes"] });
    qc.invalidateQueries({ queryKey: ["localities"] });
    qc.invalidateQueries({ queryKey: ["nsa"] });
  };

  const createCity = useMutation({
    mutationFn: (data: { name: string; state: string }) =>
      api.post("/cities", data),
    onSuccess: () => {
      invalidateAll();
      setCityDialog({ open: false });
    },
  });

  const updateCity = useMutation({
    mutationFn: ({ id, ...data }: { id: string; name: string; state: string }) =>
      api.put(`/cities/${id}`, data),
    onSuccess: () => {
      invalidateAll();
      setCityDialog({ open: false });
    },
  });

  const deleteCity = useMutation({
    mutationFn: (id: string) => api.delete(`/cities/${id}`),
    onSuccess: () => {
      invalidateAll();
      setDeleteDialog((d) => ({ ...d, open: false }));
    },
  });

  const toggleCityServiceable = useMutation({
    mutationFn: (city: City) =>
      api.put(`/cities/${city.id}/serviceable`, {
        is_serviceable: !city.is_serviceable,
      }),
    onSuccess: () => invalidateAll(),
  });

  const createZone = useMutation({
    mutationFn: (data: { name: string; city_id: string }) =>
      api.post("/zones", data),
    onSuccess: () => {
      invalidateAll();
      setZoneDialog({ open: false });
    },
  });

  const updateZone = useMutation({
    mutationFn: ({ id, ...data }: { id: string; name: string; city_id: string }) =>
      api.put(`/zones/${id}`, data),
    onSuccess: () => {
      invalidateAll();
      setZoneDialog({ open: false });
    },
  });

  const deleteZone = useMutation({
    mutationFn: (id: string) => api.delete(`/zones/${id}`),
    onSuccess: () => {
      invalidateAll();
      setDeleteDialog((d) => ({ ...d, open: false }));
    },
  });

  const toggleZoneActive = useMutation({
    mutationFn: (zone: Zone) =>
      api.put(`/zones/${zone.id}/active`, { is_active: !zone.is_active }),
    onSuccess: () => invalidateAll(),
  });

  const createPincode = useMutation({
    mutationFn: (data: { pincode: string; zone_id: string }) =>
      api.post("/pincodes", data),
    onSuccess: () => {
      invalidateAll();
      setPincodeDialog({ open: false, zoneId: "" });
    },
  });

  const deletePincode = useMutation({
    mutationFn: (id: string) => api.delete(`/pincodes/${id}`),
    onSuccess: () => {
      invalidateAll();
      setDeleteDialog((d) => ({ ...d, open: false }));
    },
  });

  const createLocality = useMutation({
    mutationFn: (data: { name: string; pincode_id: string }) =>
      api.post("/localities", data),
    onSuccess: () => {
      invalidateAll();
      setLocalityDialog({ open: false, pincodeId: "" });
    },
  });

  const deleteLocality = useMutation({
    mutationFn: (id: string) => api.delete(`/localities/${id}`),
    onSuccess: () => {
      invalidateAll();
      setDeleteDialog((d) => ({ ...d, open: false }));
    },
  });

  const markNSA = useMutation({
    mutationFn: (data: { pincode: string; reason: string }) =>
      api.post("/nsa/mark", data),
    onSuccess: () => {
      invalidateAll();
      setNsaDialog(false);
    },
  });

  const unmarkNSA = useMutation({
    mutationFn: (pincode: string) =>
      api.delete(`/nsa/unmark?pincode=${pincode}`),
    onSuccess: () => invalidateAll(),
  });

  const importCSV = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post("/zones/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: (res) => {
      setCsvResult(res.data);
      invalidateAll();
    },
  });

  // ── Handlers ───────────────────────────────────────────

  const handleCitySubmit = (data: { name: string; state: string }) => {
    if (cityDialog.city) {
      updateCity.mutate({ id: cityDialog.city.id, ...data });
    } else {
      createCity.mutate(data);
    }
  };

  const handleZoneSubmit = (data: { name: string; city_id: string }) => {
    if (zoneDialog.zone) {
      updateZone.mutate({ id: zoneDialog.zone.id, ...data });
    } else {
      createZone.mutate(data);
    }
  };

  const handlePincodeSubmit = (data: { pincode: string; zone_id: string }) => {
    createPincode.mutate(data);
  };

  const handleLocalitySubmit = (data: {
    name: string;
    pincode_id: string;
    id?: string;
  }) => {
    // Edit not supported by API — just create new
    createLocality.mutate({ name: data.name, pincode_id: data.pincode_id });
  };

  const handleMarkNSA = (pincode: string) => {
    markNSA.mutate({ pincode, reason: "" });
  };

  const handleUnmarkNSA = (pincode: string) => {
    unmarkNSA.mutate(pincode);
  };

  // ── Render ─────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Service Areas</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage cities, zones, pincodes and localities
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setCsvDialog(true)}
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
          >
            <Upload className="h-4 w-4" />
            Import CSV
          </button>
          <button
            onClick={() => setCityDialog({ open: true })}
            className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Add City
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search cities…"
          className="w-full rounded-md border border-gray-300 pl-10 pr-9 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute right-3 top-1/2 -translate-y-1/2"
          >
            <X className="h-4 w-4 text-gray-400" />
          </button>
        )}
      </div>

      {/* Tree */}
      <div className="rounded-lg border bg-white shadow-sm">
        {cities.isLoading ? (
          <div className="p-8 text-center text-sm text-gray-400">
            Loading service areas…
          </div>
        ) : filteredCities.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">
            {search ? "No cities match your search." : "No cities yet. Add one to get started."}
          </div>
        ) : (
          filteredCities.map((city) => (
            <CityRow
              key={city.id}
              city={city}
              nsaSet={nsaSet}
              onToggleServiceable={(c) => toggleCityServiceable.mutate(c)}
              onEdit={(c) => setCityDialog({ open: true, city: c })}
              onDelete={(c) =>
                setDeleteDialog({
                  open: true,
                  title: "Delete City",
                  description: `Are you sure you want to delete "${c.name}"? This cannot be undone.`,
                  onConfirm: () => deleteCity.mutate(c.id),
                })
              }
              onAddZone={(cityId) =>
                setZoneDialog({ open: true, cityId })
              }
              onEditZone={(z) => setZoneDialog({ open: true, zone: z })}
              onDeleteZone={(z) =>
                setDeleteDialog({
                  open: true,
                  title: "Delete Zone",
                  description: `Are you sure you want to delete zone "${z.name}"?`,
                  onConfirm: () => deleteZone.mutate(z.id),
                })
              }
              onToggleZoneActive={(z) => toggleZoneActive.mutate(z)}
              onAddPincode={(zoneId) =>
                setPincodeDialog({ open: true, zoneId })
              }
              onDeletePincode={(p) =>
                setDeleteDialog({
                  open: true,
                  title: "Delete Pincode",
                  description: `Are you sure you want to delete pincode ${p.pincode}?`,
                  onConfirm: () => deletePincode.mutate(p.id),
                })
              }
              onMarkNSA={handleMarkNSA}
              onUnmarkNSA={handleUnmarkNSA}
              onAddLocality={(pincodeId) =>
                setLocalityDialog({ open: true, pincodeId })
              }
              onEditLocality={(loc) =>
                setLocalityDialog({
                  open: true,
                  locality: loc,
                  pincodeId: loc.pincode_id,
                })
              }
              onDeleteLocality={(loc) =>
                setDeleteDialog({
                  open: true,
                  title: "Delete Locality",
                  description: `Are you sure you want to delete locality "${loc.name}"?`,
                  onConfirm: () => deleteLocality.mutate(loc.id),
                })
              }
            />
          ))
        )}
      </div>

      {/* Dialogs */}
      <CityDialog
        open={cityDialog.open}
        onClose={() => setCityDialog({ open: false })}
        city={cityDialog.city}
        onSubmit={handleCitySubmit}
        loading={createCity.isPending || updateCity.isPending}
      />

      <ZoneDialog
        open={zoneDialog.open}
        onClose={() => setZoneDialog({ open: false })}
        zone={zoneDialog.zone}
        cityId={zoneDialog.cityId}
        cities={cities.data?.items ?? []}
        onSubmit={handleZoneSubmit}
        loading={createZone.isPending || updateZone.isPending}
      />

      <PincodeDialog
        open={pincodeDialog.open}
        onClose={() => setPincodeDialog({ open: false, zoneId: "" })}
        zoneId={pincodeDialog.zoneId}
        onSubmit={handlePincodeSubmit}
        loading={createPincode.isPending}
      />

      <LocalityDialog
        open={localityDialog.open}
        onClose={() => setLocalityDialog({ open: false, pincodeId: "" })}
        locality={localityDialog.locality}
        pincodeId={localityDialog.pincodeId}
        onSubmit={handleLocalitySubmit}
        loading={createLocality.isPending}
      />

      <NSADialog
        open={nsaDialog}
        onClose={() => setNsaDialog(false)}
        onSubmit={(data) => markNSA.mutate(data)}
        loading={markNSA.isPending}
      />

      <CSVImportDialog
        open={csvDialog}
        onClose={() => {
          setCsvDialog(false);
          setCsvResult(undefined);
        }}
        onUpload={(file) => importCSV.mutate(file)}
        loading={importCSV.isPending}
        result={csvResult}
      />

      <DeleteConfirmDialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog((d) => ({ ...d, open: false }))}
        onConfirm={deleteDialog.onConfirm}
        title={deleteDialog.title}
        description={deleteDialog.description}
        loading={
          deleteCity.isPending ||
          deleteZone.isPending ||
          deletePincode.isPending ||
          deleteLocality.isPending
        }
      />
    </div>
  );
}
