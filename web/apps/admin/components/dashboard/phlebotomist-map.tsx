"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MapPin } from "lucide-react";

interface PhlebotomistLocation {
  id: string;
  name: string;
  lat: number;
  lng: number;
  status: "active" | "idle" | "offline";
}

interface PhlebotomistMapProps {
  locations?: PhlebotomistLocation[];
  isLoading?: boolean;
}

export function PhlebotomistMap({ locations = [], isLoading }: PhlebotomistMapProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Phlebotomist Locations</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative flex h-[350px] items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 bg-muted/30">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading map…</p>
          ) : (
            <div className="flex flex-col items-center gap-3 text-muted-foreground">
              <MapPin className="h-10 w-10" />
              <p className="text-sm font-medium">Google Maps Integration</p>
              <p className="text-xs">
                {locations.length > 0
                  ? `${locations.length} phlebotomist(s) tracked`
                  : "Map will show live phlebotomist locations"}
              </p>
              {locations.length > 0 && (
                <div className="mt-2 flex flex-wrap justify-center gap-2">
                  {locations.map((loc) => (
                    <span
                      key={loc.id}
                      className="inline-flex items-center gap-1 rounded-full bg-background px-2 py-1 text-xs shadow-sm"
                    >
                      <span
                        className={`h-2 w-2 rounded-full ${
                          loc.status === "active"
                            ? "bg-green-500"
                            : loc.status === "idle"
                              ? "bg-yellow-500"
                              : "bg-gray-400"
                        }`}
                      />
                      {loc.name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
