"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/", icon: "home", label: "Home" },
  { href: "/services", icon: "medical_services", label: "Services" },
  { href: "/about", icon: "info", label: "About" },
  { href: "/for-labs", icon: "handshake", label: "Partners" },
  { href: "/contact", icon: "person", label: "Profile" },
];

export default function MobileTabBar() {
  const pathname = usePathname();
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-xl border-t border-slate-200 pb-[env(safe-area-inset-bottom)]">
      <div className="flex justify-around items-center px-4 py-3">
        {tabs.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex flex-col items-center gap-1 ${active ? "text-primary" : "text-slate-400"}`}
            >
              <span
                className="material-symbols-outlined"
                style={active ? { fontVariationSettings: "'FILL' 1" } : {}}
              >
                {tab.icon}
              </span>
              <span className="text-[10px] font-bold uppercase tracking-tighter">
                {tab.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
