import Link from "next/link";

export const metadata = { title: "Services - Prick & Care" };

export default function ServicesPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative w-full overflow-hidden">
        <div className="bg-primary px-6 py-12 md:py-20 flex flex-col gap-4 text-white relative">
          <div className="absolute inset-0 opacity-10 pointer-events-none bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-white via-transparent to-transparent"></div>
          <div className="max-w-7xl mx-auto w-full flex flex-col gap-1 z-10">
            <nav className="flex items-center gap-2 text-white/60 text-xs font-medium uppercase tracking-widest mb-2">
              <Link href="/">Home</Link>
              <span className="material-symbols-outlined text-[10px]">chevron_right</span>
              <span className="text-white">Services</span>
            </nav>
            <h1 className="text-4xl md:text-5xl font-black leading-tight tracking-tight">Our Services</h1>
            <p className="text-white/80 text-base md:text-lg leading-relaxed max-w-lg mt-2">
              Comprehensive phlebotomy solutions designed for hospitals, diagnostic labs, and corporate partners.
            </p>
            <div className="mt-4">
              <button className="bg-white text-primary px-6 py-3 rounded-xl font-bold text-sm shadow-lg shadow-black/10 active:scale-95 transition-transform">
                Explore Offerings
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Service 1: Home Sample Collection */}
      <section className="px-4 py-8 md:py-16 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 mb-6">
          <div className="h-1 w-12 bg-primary rounded-full"></div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-primary">Healthcare at Doorstep</h3>
        </div>
        <div className="rounded-2xl overflow-hidden shadow-sm border border-slate-200 bg-white grid grid-cols-1 lg:grid-cols-2">
          <div
            className="h-56 lg:h-auto w-full bg-slate-100 bg-cover bg-center"
            style={{
              backgroundImage:
                "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDV9HufPoI2La6VxXWMBCyBAstspmXmaGf_Xb1uMHY4DDV9J1dbm5dwTGYrbzq9lufvmKFFKQdHBAouYBO7RFKR2ABO0-HuhUci9wkXaYU-WJn6nTPcTakMMJEFz5aI24kR_s6-u8NE25T2uZ3sFdIS9VPedNl4Om1VXAJ2kizdpewq2M2vIbom4rdPokWxCsVRU1dVf2Pyaf_EL1ijSZrZVAiOGr1rv3N9gIjzsqCrP8nrHo1FTP57Eqr9r9lNrOVRcfwCokmkZjQ')",
            }}
          ></div>
          <div className="p-6 md:p-10">
            <h4 className="text-2xl font-bold text-slate-900 mb-3">Home Sample Collection</h4>
            <p className="text-slate-600 mb-6 leading-relaxed">
              Professional phlebotomy services delivered to patients&apos; homes with 100% compliance and safety standards.
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                { icon: "badge", label: "Trained Staff" },
                { icon: "location_on", label: "GPS Tracking" },
                { icon: "verified_user", label: "OTP Verified" },
              ].map((tag) => (
                <span key={tag.label} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-xs font-semibold">
                  <span className="material-symbols-outlined text-sm">{tag.icon}</span> {tag.label}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Service 2: Corporate Health Camps */}
      <section className="px-4 py-8 md:py-16 bg-slate-50">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-2 mb-6">
            <div className="h-1 w-12 bg-primary rounded-full"></div>
            <h3 className="text-xs font-bold uppercase tracking-widest text-primary">B2B Volume Solutions</h3>
          </div>
          <div className="rounded-2xl overflow-hidden shadow-sm border border-slate-200 bg-white grid grid-cols-1 lg:grid-cols-2">
            <div className="p-6 md:p-10 order-2 lg:order-1">
              <h4 className="text-2xl font-bold text-slate-900 mb-3">Corporate Health Camps</h4>
              <p className="text-slate-600 mb-6 leading-relaxed">
                Seamless bulk collection drives for employee wellness programs with rapid on-site setup and management.
              </p>
              <ul className="space-y-3 mb-6">
                <li className="flex items-start gap-3 text-sm text-slate-700">
                  <span className="material-symbols-outlined text-primary text-xl">check_circle</span>
                  <span>Scalable teams for 500+ employees</span>
                </li>
                <li className="flex items-start gap-3 text-sm text-slate-700">
                  <span className="material-symbols-outlined text-primary text-xl">check_circle</span>
                  <span>Full equipment &amp; logistics support</span>
                </li>
              </ul>
              <button className="w-full lg:w-auto py-3 px-8 border-2 border-primary text-primary font-bold rounded-xl active:bg-primary/5">
                Inquire for Camps
              </button>
            </div>
            <div
              className="h-56 lg:h-auto w-full bg-slate-100 bg-cover bg-center order-1 lg:order-2"
              style={{
                backgroundImage:
                  "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCVvcv_naTC_JD3zxffKnstbkYwLiONe67YRLa1QxjCxwA-gM2icc4pFo8zKMDC1TiV4LeZ8S-PX_A0JcTi2oL8m7kfolpT6gLavDyT1VGIDzr4JsZhAxaLwdBw3ia1yR1TjHnQLVM2hX0ekpPpt5lUDn1TTPkiukjzAWu8H3rNo4jv6oEzuKIPamosCZS1O2k3jLh-PRo2YAuilJMm0VqcrUO9iwUXoKkKdPNY9mE05eqAjF15yQHLJGf8KMBib9BwqQ4t583F6Tc')",
              }}
            ></div>
          </div>
        </div>
      </section>

      {/* Service 3: Lab Pickup & Logistics */}
      <section className="px-4 py-8 md:py-16 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 mb-6">
          <div className="h-1 w-12 bg-primary rounded-full"></div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-primary">Supply Chain Integrity</h3>
        </div>
        <div className="rounded-2xl overflow-hidden shadow-sm border border-slate-200 bg-white grid grid-cols-1 lg:grid-cols-2">
          <div
            className="h-56 lg:h-auto w-full bg-slate-100 bg-cover bg-center"
            style={{
              backgroundImage:
                "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCapVi8yfqRJs0y8OXYUw2zcePqKUaz2S5fBL4_oV5Dl_JOeE7jMlYv3zunEcFHmJkTAcQ29CJVcLKhPEnp7i4yUmsY5Z6k2ZH82dgH-HE0ptGZHmMXnh7ohEP_7Rf3ZA3tIEA7_RBU7OG8SXBxiSydVS7tjevzev314mJPwFCi8Xi5e9wTcHUlUD-et7G_pHHJMNv3R8eO8aWoSvsSlAK3sax-6jz7GlOeOzCRWzrlwM6cZgFY6EMsnwrAkXdxKA4fZZdtfxvTmD0')",
            }}
          ></div>
          <div className="p-6 md:p-10">
            <h4 className="text-2xl font-bold text-slate-900 mb-3">Lab Pickup &amp; Logistics</h4>
            <p className="text-slate-600 mb-6 leading-relaxed">
              Precision logistics for diagnostic samples ensuring temperature control and real-time monitoring.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-background-light border border-slate-100">
                <span className="material-symbols-outlined text-primary mb-2">ac_unit</span>
                <p className="text-sm font-bold">Cold Chain</p>
                <p className="text-xs text-slate-500">2-8°C Stable</p>
              </div>
              <div className="p-4 rounded-xl bg-background-light border border-slate-100">
                <span className="material-symbols-outlined text-primary mb-2">schedule</span>
                <p className="text-sm font-bold">Daily Pickups</p>
                <p className="text-xs text-slate-500">Scheduled routes</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Service 4: Technology Platform */}
      <section className="px-4 py-8 md:py-16 bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-2 mb-6">
            <div className="h-1 w-12 bg-primary rounded-full"></div>
            <h3 className="text-xs font-bold uppercase tracking-widest text-primary">Digital Infrastructure</h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="flex flex-col gap-4">
              <h4 className="text-3xl font-black tracking-tight">Technology Platform</h4>
              <p className="text-slate-400 leading-relaxed">
                A robust admin panel for labs to monitor every prick, every route, and every report in real-time.
              </p>
              <div className="mt-4 relative bg-slate-800 p-4 rounded-2xl border border-slate-700 shadow-2xl">
                <div className="w-full aspect-[4/3] rounded-lg bg-slate-950 overflow-hidden relative">
                  <div className="absolute inset-0 p-4 flex flex-col gap-3">
                    <div className="flex justify-between items-center">
                      <div className="h-4 w-24 bg-primary/40 rounded"></div>
                      <div className="size-6 bg-slate-700 rounded-full"></div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="h-16 bg-slate-800 rounded-lg flex flex-col p-2 gap-1">
                        <div className="h-2 w-8 bg-slate-600 rounded"></div>
                        <div className="h-4 w-12 bg-primary/60 rounded"></div>
                      </div>
                      <div className="h-16 bg-slate-800 rounded-lg flex flex-col p-2 gap-1">
                        <div className="h-2 w-8 bg-slate-600 rounded"></div>
                        <div className="h-4 w-12 bg-green-500/60 rounded"></div>
                      </div>
                      <div className="h-16 bg-slate-800 rounded-lg flex flex-col p-2 gap-1">
                        <div className="h-2 w-8 bg-slate-600 rounded"></div>
                        <div className="h-4 w-12 bg-yellow-500/60 rounded"></div>
                      </div>
                    </div>
                    <div className="flex-1 bg-slate-900/50 rounded-lg border border-slate-800 p-2">
                      <div className="space-y-2">
                        <div className="h-2 w-full bg-slate-800 rounded"></div>
                        <div className="h-2 w-3/4 bg-slate-800 rounded"></div>
                        <div className="h-2 w-1/2 bg-slate-800 rounded"></div>
                      </div>
                    </div>
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-transparent pointer-events-none"></div>
                </div>
              </div>
            </div>
            <div className="flex flex-col justify-center gap-4 mt-4 lg:mt-0">
              {[
                { icon: "api", title: "API Integration", desc: "Connect to your LIS/HIS" },
                { icon: "analytics", title: "MIS Reports", desc: "Automated daily insights" },
              ].map((item) => (
                <div key={item.title} className="flex items-center gap-4">
                  <span className="material-symbols-outlined text-primary p-2 bg-primary/10 rounded-lg">{item.icon}</span>
                  <div>
                    <p className="font-bold">{item.title}</p>
                    <p className="text-xs text-slate-500">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="px-6 py-12 md:py-20 text-center bg-white">
        <div className="max-w-2xl mx-auto">
          <h4 className="text-2xl md:text-3xl font-black text-slate-900 mb-4">Need a Custom Solution?</h4>
          <p className="text-slate-600 mb-8 max-w-md mx-auto">
            Talk to our experts for tailor-made phlebotomy and logistics operations for your network.
          </p>
          <Link
            href="/contact"
            className="inline-block bg-primary hover:bg-primary/90 text-navy-accent w-full md:w-auto py-4 px-10 rounded-xl font-black text-lg shadow-xl shadow-primary/20 transition-all active:scale-95"
          >
            Contact Our Team
          </Link>
        </div>
      </section>
    </>
  );
}
