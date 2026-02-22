import Link from "next/link";

export const metadata = { title: "About Us - Prick & Care" };

export default function AboutPage() {
  return (
    <>
      {/* Hero */}
      <section className="px-4 py-8 md:py-16 max-w-7xl mx-auto">
        <div className="relative overflow-hidden rounded-xl bg-slate-900 p-8 md:p-16 text-white">
          <div
            className="absolute inset-0 opacity-20 bg-cover bg-center"
            style={{
              backgroundImage:
                "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDcNqFMYXEZQp5zSHez4k9N0ZusykLTOICQqfSHidU8Ud9CEgL7XxPb5XYt1fZa1VkJ2UC5jEz6GJoKGsdW1CZXLX3tEnhX-SZiwcmmXfTgKRUZqRiQvXHAitcHVJl9hoYebfZkpWdq_vg6kDkO9B8TWWNtZPO-6Out5KYvjghdWtcAlEtJjbHaICTQ4nGI_otbED-nHBnmmyeivNeicEQpS6ufF8pTTaW1He8Jm7v2KsS4r67AuVTi82SJI9fr1xk-iZsWYph5FZA')",
            }}
          ></div>
          <div className="relative z-10 flex flex-col gap-4 max-w-2xl">
            <span className="inline-block w-fit px-3 py-1 text-xs font-bold uppercase tracking-wider bg-primary text-slate-900 rounded-full">
              B2B Phlebotomy Logistics
            </span>
            <h1 className="text-3xl md:text-5xl font-black leading-tight">About Prick &amp; Care</h1>
            <p className="text-slate-300 text-sm md:text-base leading-relaxed">
              Revolutionizing phlebotomy logistics for diagnostic labs and hospitals with speed, precision, and patient-centric care.
            </p>
            <Link
              href="/for-labs"
              className="mt-2 flex w-fit items-center justify-center rounded-lg bg-primary px-6 py-3 text-sm font-bold text-slate-900"
            >
              Partner With Us
            </Link>
          </div>
        </div>
      </section>

      {/* Mission & Vision */}
      <section className="px-4 max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm">
          <div className="flex items-center gap-3 mb-3 text-primary">
            <span className="material-symbols-outlined">rocket_launch</span>
            <h3 className="text-lg font-bold text-slate-900">Our Mission</h3>
          </div>
          <p className="text-sm text-slate-600">
            To bridge the gap between diagnostic excellence and patient accessibility through tech-enabled mobile phlebotomy.
          </p>
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm">
          <div className="flex items-center gap-3 mb-3 text-primary">
            <span className="material-symbols-outlined">visibility</span>
            <h3 className="text-lg font-bold text-slate-900">Our Vision</h3>
          </div>
          <p className="text-sm text-slate-600">
            To be the global gold standard for clinical sample logistics, ensuring every patient receives hospital-grade care at home.
          </p>
        </div>
      </section>

      {/* Story Timeline */}
      <section className="px-4 py-10 max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold mb-8">Our Story</h2>
        <div className="relative ml-4 border-l-2 border-primary/30 pl-8 space-y-10">
          {[
            { year: "2024", title: "Founded in Mumbai", desc: "Started our journey to bridge the gap between labs and patient homes.", active: true },
            { year: "2025", title: "Regional Expansion", desc: "Expanding services across 15+ major metropolitan areas and tier-2 cities.", active: false },
            { year: "2026 Goal", title: "200+ Partners", desc: "Serving a network of top hospitals and diagnostic chains nationwide.", active: false },
          ].map((item) => (
            <div key={item.year} className="relative">
              <div className={`absolute -left-[41px] top-0 size-5 rounded-full border-4 border-background-light ${item.active ? "bg-primary" : "bg-primary/40"}`}></div>
              <h4 className={`font-bold mb-1 ${item.active ? "text-primary" : "text-slate-500"}`}>{item.year}</h4>
              <p className="font-bold text-slate-900">{item.title}</p>
              <p className="text-sm text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Values */}
      <section className="px-4 py-8 bg-slate-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold mb-6">Our Core Values</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: "verified", title: "Quality First", desc: "Standardized clinical protocols." },
              { icon: "shield_with_heart", title: "Trust", desc: "Secure sample handling." },
              { icon: "devices", title: "Technology", desc: "API-first logistics platform." },
              { icon: "health_and_safety", title: "Comfort", desc: "Expert phlebotomy team." },
            ].map((val) => (
              <div key={val.title} className="bg-white p-4 rounded-xl shadow-sm border border-slate-100">
                <span className="material-symbols-outlined text-primary mb-2">{val.icon}</span>
                <h4 className="font-bold text-sm mb-1">{val.title}</h4>
                <p className="text-xs text-slate-500">{val.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Leadership */}
      <section className="px-4 py-10 max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold mb-6">Our Leadership</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { name: "Dr. Arjan Mehta", role: "Founder & CEO", img: "https://lh3.googleusercontent.com/aida-public/AB6AXuCPHTU5ST6ubsF-stnzrczZjGU33LAFeXroQOIu_UwKHqUTUXaZoxsOYlnczd6tWFIExkJcOrQJGVHvReT-PXmHR60TYSYpbYiBDorlWSf9Gh69ZRRF2IVZQrKw6Ld04vz0Mrhe7Zz1MlnOMA3v_WbLcOR_l_eAhoB8I9wlkRl1QEVQIvASBkKMnJsC7-clOrzcNmd-C8JKQrVTlymJkpiqCIqM8vHaX3CdskkMQ2O18oLj9XqsoFULFPG73EwCBn8ebwcUbflaxsI" },
            { name: "Sarah Jenkins", role: "COO", img: "https://lh3.googleusercontent.com/aida-public/AB6AXuDxcr-wXUTwbuqzkArMbW8XxXM18Jac6T6ilNFDIkaahVvDE3dMb4slmAAjNRRhb45z3eLRa8C2adQdCjt_wxThuZIYVJZv0K3tJ9f7cEimSfmtKnCez7gYQlQSg9aOMcK0UWNQaS4HiZoVj2nXqIA4Xq_vr-qDg2tLhURpBd4RTW-DfhztDvEzE1i-6YZoPWvL_Z-vyDm-CZW6jTSXrH1T7Cn3bagZTT9jsujbnLmyyzYcFDVQMBEpw8UDGCNPSQUNFgnCAbmzFmQ" },
            { name: "Vikram Singh", role: "CTO", img: "https://lh3.googleusercontent.com/aida-public/AB6AXuBSacG8FNkU5zdeQaFxsxzfTIjUrqyl_56wZLDC8DBkFApvSdCCHRqoyILn0RdOEyzYRj5h8bSGXeBx4EWKHbhWtlE4f6eza_NvG-yDFWR03xhHX1Hac_3HQlrOq1uJLvZQGyv0kajGBUZ1kaIaHQOLXQ0WMCH-vDRrEE-a3_OZVboiFfTaWNZmAQZ72wB0gmlLqKvFDO8LnJtqAfqTM5yTjBoqq3fpK73JP9_dL7ktIQbaB_ibbB1k7XI2JSG-laMIhzKhIFxkr8g" },
            { name: "Elena Rodriguez", role: "Head of Ops", img: "https://lh3.googleusercontent.com/aida-public/AB6AXuCdm3YAjO9PyAhpLGqHFhn8mX2YEz_2tcurXPH3yzhRAcwWWQ1f1D1rhpHGL7iOi2zS7FI3k7Qmd_xqJbkQqfE6VZqNiR7Kg5J-_U_lvqm02-LckryZGHbEU4yj55c_Qypl4kjdMulvy9yu8m9Nj-f44Faat1ncoYWuNlxehkZ6PrsyLBwUz8MvHobdk7AFbGWLtWBGZEOfFSVCTvWiNejAwtknt_rwEtVJEomW8VYXRlaeGHWZWh0c7TkYdd5pU47g-ZDt5TiGbL8" },
          ].map((leader) => (
            <div key={leader.name} className="flex flex-col items-center text-center">
              <div
                className="size-24 rounded-full overflow-hidden mb-3 border-2 border-primary/20 bg-slate-200 bg-cover bg-center"
                style={{ backgroundImage: `url('${leader.img}')` }}
              ></div>
              <h4 className="font-bold text-sm">{leader.name}</h4>
              <p className="text-xs text-slate-500">{leader.role}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Certifications */}
      <section className="px-4 py-8 mb-4 border-t border-slate-200">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-xs font-bold uppercase tracking-widest text-slate-400 mb-6">Certifications &amp; Compliance</p>
          <div className="flex justify-center gap-12 items-center grayscale opacity-60">
            {[
              { icon: "security", label: "HIPAA COMPLIANT" },
              { icon: "clinical_notes", label: "NABL AWARE" },
              { icon: "verified_user", label: "ISO 9001:2015" },
            ].map((cert) => (
              <div key={cert.label} className="flex flex-col items-center">
                <span className="material-symbols-outlined text-4xl mb-1">{cert.icon}</span>
                <span className="text-[10px] font-black">{cert.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
