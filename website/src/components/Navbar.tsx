"use client";
import Link from "next/link";
import { useState } from "react";

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="flex items-center justify-between px-4 h-16 max-w-7xl mx-auto">
        <Link href="/" className="flex items-center gap-2">
          <div className="bg-primary p-1.5 rounded-lg">
            <span className="material-symbols-outlined text-navy-accent text-2xl">
              biotech
            </span>
          </div>
          <span className="text-xl font-bold tracking-tight text-navy-accent leading-none">
            Prick &amp; Care
          </span>
        </Link>
        <div className="flex items-center gap-3">
          {/* Desktop nav links */}
          <div className="hidden lg:flex items-center gap-6 mr-4">
            <Link href="/services" className="text-sm font-medium text-slate-600 hover:text-primary">Services</Link>
            <Link href="/for-labs" className="text-sm font-medium text-slate-600 hover:text-primary">For Labs</Link>
            <Link href="/about" className="text-sm font-medium text-slate-600 hover:text-primary">About</Link>
            <Link href="/careers" className="text-sm font-medium text-slate-600 hover:text-primary">Careers</Link>
            <Link href="/contact" className="text-sm font-medium text-slate-600 hover:text-primary">Contact</Link>
          </div>
          <button className="hidden md:flex text-sm font-semibold px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50">
            Client Login
          </button>
          <Link
            href="/request-demo"
            className="bg-primary text-navy-accent text-sm font-bold px-4 py-2 rounded-lg shadow-sm hover:opacity-90 active:scale-95 transition-all"
          >
            Request Demo
          </Link>
          <button
            className="p-2 text-slate-600 lg:hidden"
            onClick={() => setOpen(!open)}
          >
            <span className="material-symbols-outlined">
              {open ? "close" : "menu"}
            </span>
          </button>
        </div>
      </div>
      {/* Mobile menu */}
      {open && (
        <div className="lg:hidden border-t border-slate-200 bg-white px-4 py-4 space-y-3">
          <Link href="/services" className="block text-sm font-medium text-slate-700 hover:text-primary" onClick={() => setOpen(false)}>Services</Link>
          <Link href="/for-labs" className="block text-sm font-medium text-slate-700 hover:text-primary" onClick={() => setOpen(false)}>For Labs</Link>
          <Link href="/about" className="block text-sm font-medium text-slate-700 hover:text-primary" onClick={() => setOpen(false)}>About</Link>
          <Link href="/careers" className="block text-sm font-medium text-slate-700 hover:text-primary" onClick={() => setOpen(false)}>Careers</Link>
          <Link href="/contact" className="block text-sm font-medium text-slate-700 hover:text-primary" onClick={() => setOpen(false)}>Contact</Link>
        </div>
      )}
    </nav>
  );
}
