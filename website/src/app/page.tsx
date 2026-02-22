import Link from "next/link";

export default function HomePage() {
  return (
    <>
      {/* Hero Section */}
      <section className="relative px-4 py-12 md:py-20 overflow-hidden">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div className="space-y-6 z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold uppercase tracking-wider">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
              </span>
              India&apos;s #1 B2B Phlebotomy Service
            </div>
            <h1 className="text-4xl md:text-6xl font-black text-navy-accent leading-[1.1] tracking-tight">
              India&apos;s Most Reliable <br />
              <span className="text-primary">Phlebotomy Partner</span>
            </h1>
            <p className="text-slate-600 text-base md:text-lg leading-relaxed max-w-xl">
              Partner with India&apos;s leading B2B phlebotomy service provider for diagnostic labs and hospitals. Ensuring sample integrity, cold-chain logistics, and 24/7 reliability.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link
                href="/request-demo"
                className="flex items-center justify-center gap-2 bg-primary text-navy-accent font-bold py-4 px-8 rounded-xl shadow-lg shadow-primary/20 hover:scale-105 transition-transform"
              >
                Request a Demo
                <span className="material-symbols-outlined">arrow_forward</span>
              </Link>
              <button className="flex items-center justify-center gap-2 bg-white border border-slate-200 text-navy-accent font-bold py-4 px-8 rounded-xl hover:bg-slate-50 transition-colors">
                Download Brochure
                <span className="material-symbols-outlined">download</span>
              </button>
            </div>
          </div>
          <div className="relative group">
            <div className="absolute -inset-4 bg-primary/10 rounded-3xl blur-2xl group-hover:bg-primary/20 transition-all"></div>
            <div
              className="relative w-full aspect-[4/3] rounded-2xl overflow-hidden shadow-2xl bg-slate-200 bg-cover bg-center"
              style={{
                backgroundImage:
                  "url('https://lh3.googleusercontent.com/aida-public/AB6AXuAweAXDBYJODfEfmhDOjCIU2a0vd4tgrx5KQ2KcypWUbBDxk2B9bl-4c-eInQFehe6pm-dbI640bH1x5s_6tXD2ZH0tz5eizNvepQI-N7MMO0UXWLTgkFmCyPXzZvR7BQ_QFnlFRSUXwLMIihDqiNtktiaB2HLM2Z1AJHjVOTRNzaSKkjlMXDNq2lrdi5KqFJ-ory6CL0eAruisN7gALQWXSs6xb7hl6IYAZPooD1FKpNVbPpl7bmAB0NmL7dMTNBZpdjQWb6kGYds')",
              }}
            ></div>
            <div className="absolute -bottom-6 -left-6 bg-white p-4 rounded-xl shadow-xl border border-slate-100 hidden sm:flex items-center gap-4">
              <div className="size-12 rounded-full bg-primary/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary">verified_user</span>
              </div>
              <div>
                <p className="text-sm font-bold text-navy-accent">NABL Compliant</p>
                <p className="text-xs text-slate-500">ISO 15189 standards followed</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Bar */}
      <div className="bg-slate-50 py-10 border-y border-slate-100">
        <p className="text-center text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-8">
          Trusted by leading diagnostic giants
        </p>
        <div className="flex overflow-hidden group">
          <div className="flex space-x-12 animate-marquee whitespace-nowrap px-4 opacity-50 grayscale hover:grayscale-0 transition-all">
            {["LAL PATHLABS", "METROPOLIS", "THYROCARE", "SRL DIAGNOSTICS", "APOLLO 247", "HCG HOSPITALS"].map((name) => (
              <div key={name} className="h-10 w-32 bg-slate-300 rounded-lg flex items-center justify-center text-xs font-bold">
                {name}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <section className="px-4 py-16 max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: "bloodtype", value: "50k+", label: "Monthly Collections" },
            { icon: "business_center", value: "200+", label: "Lab Partners" },
            { icon: "location_on", value: "15+", label: "Major Cities" },
            { icon: "task_alt", value: "99.2%", label: "Integrity Rate" },
          ].map((stat) => (
            <div key={stat.label} className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm text-center md:text-left">
              <span className="material-symbols-outlined text-primary text-3xl mb-2">{stat.icon}</span>
              <p className="text-3xl font-black text-navy-accent">{stat.value}</p>
              <p className="text-sm font-medium text-slate-500">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Services Grid */}
      <section className="px-4 py-16 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-3xl font-black text-navy-accent mb-4">Our Core Solutions</h2>
            <p className="text-slate-500">End-to-end clinical sample management tailored for modern healthcare infrastructure.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: "home_health", title: "Home Collection", desc: "On-demand home visits for patient sample collection with real-time slot booking." },
              { icon: "groups", title: "Corporate Camps", desc: "Mass screening and sample collection drives for large organizations and complexes." },
              { icon: "local_shipping", title: "Lab-to-Lab Pickup", desc: "Secure transport of specialty samples between small labs and reference centers." },
              { icon: "distance", title: "Live Tracking", desc: "GPS-enabled sample tracking from the patient's doorstep to the lab accessioning." },
            ].map((svc) => (
              <div key={svc.title} className="group p-8 rounded-2xl bg-background-light hover:bg-primary/5 transition-colors border border-transparent hover:border-primary/20">
                <div className="size-14 rounded-xl bg-primary/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <span className="material-symbols-outlined text-primary text-3xl">{svc.icon}</span>
                </div>
                <h3 className="text-xl font-bold text-navy-accent mb-3">{svc.title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed mb-4">{svc.desc}</p>
                <Link className="text-primary text-sm font-bold flex items-center gap-1 group-hover:gap-2 transition-all" href="/services">
                  Learn more <span className="material-symbols-outlined text-sm">arrow_forward</span>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="px-4 py-16 bg-slate-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-black text-navy-accent text-center mb-16">The Seamless Workflow</h2>
          <div className="space-y-12 relative before:content-[''] before:absolute before:left-8 md:before:left-1/2 before:top-0 before:bottom-0 before:w-0.5 before:bg-primary/20 before:-translate-x-1/2">
            {[
              { num: 1, title: "API Integration", desc: "Connect your LIMS with our booking engine via robust REST APIs for instant order sync.", side: "left" },
              { num: 2, title: "Smart Allocation", desc: "AI assigns the nearest verified phlebotomist equipped with cold-chain carrying gear.", side: "right" },
              { num: 3, title: "Sterile Collection", desc: "Professional phlebotomists follow strict SOPs for collection and barcoding on-site.", side: "left" },
              { num: 4, title: "Real-time Handover", desc: "Samples delivered to your lab within 90 minutes. Digital proof of handover generated.", side: "right" },
            ].map((step) => (
              <div key={step.num} className="relative flex items-center gap-8 flex-col md:flex-row">
                <div className="absolute left-8 md:left-1/2 size-8 bg-primary rounded-full flex items-center justify-center text-navy-accent font-bold -translate-x-1/2 z-10 border-4 border-white">
                  {step.num}
                </div>
                {step.side === "left" ? (
                  <>
                    <div className="w-full md:w-1/2 pl-16 md:pl-0 md:pr-16 text-left md:text-right">
                      <h4 className="text-xl font-bold text-navy-accent mb-2">{step.title}</h4>
                      <p className="text-slate-500 text-sm">{step.desc}</p>
                    </div>
                    <div className="hidden md:block w-1/2"></div>
                  </>
                ) : (
                  <>
                    <div className="hidden md:block w-1/2"></div>
                    <div className="w-full md:w-1/2 pl-16 md:pr-0 text-left">
                      <h4 className="text-xl font-bold text-navy-accent mb-2">{step.title}</h4>
                      <p className="text-slate-500 text-sm">{step.desc}</p>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Choose Us */}
      <section className="px-4 py-16 max-w-7xl mx-auto">
        <h2 className="text-3xl font-black text-navy-accent text-center mb-12">The Prick &amp; Care Advantage</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { icon: "schedule", title: "Zero Turn-Downs", desc: "Scale your collection capacity instantly during morning peak hours." },
            { icon: "ac_unit", title: "Active Cold Chain", desc: "Integrated thermal monitoring ensuring samples stay between 2°C - 8°C." },
            { icon: "security", title: "Verified Talent", desc: "100% background-checked phlebotomists with DMLT/BMLT certifications." },
            { icon: "payments", title: "Smart Settlements", desc: "Real-time payment collection (UPI/Cash) with automated lab reconciliation." },
            { icon: "bar_chart", title: "Data Insights", desc: "Detailed heatmaps of your customer demand to help you expand strategically." },
            { icon: "headset_mic", title: "24/7 Ops Support", desc: "Dedicated operational desk to manage emergency collections and logistics." },
          ].map((adv) => (
            <div key={adv.title} className="flex gap-4">
              <div className="shrink-0 size-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary">{adv.icon}</span>
              </div>
              <div>
                <h5 className="text-lg font-bold text-navy-accent mb-2">{adv.title}</h5>
                <p className="text-sm text-slate-500">{adv.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials */}
      <section className="px-4 py-16 bg-white overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-black text-navy-accent text-center mb-12">Trusted by Clinical Leaders</h2>
          <div className="flex overflow-x-auto gap-6 hide-scrollbar snap-x pb-4">
            {[
              {
                quote: "Prick & Care has revolutionized our home collection logistics. We saw a 40% increase in patient bookings within the first quarter of partnership.",
                name: "Dr. Anjali Verma",
                role: "Director, City Diagnostics",
                img: "https://lh3.googleusercontent.com/aida-public/AB6AXuDtyNRLUqhHAPaaN2mUQNUHmIzw5M67PMBcEoyHxvBE-H3ADQwY-glVJ7eCfVQLoNyNsScDdHfB8boah4TfGaB-JqrKuHvsHV1RP8k88iDSZfLA51Lz-nVIJmnz5wp1m678XLRODjtwCUso9drQ3NX6ylPaKQYyQFowkat6XaWqEEzhcQlK8W8kMlLuyLHzPY8I3fAaJAK81bTJ_vjqH40a4QF8Zt0vs0abIdr-4s4oYE7bFW6Ng7vDfrKQc5pv84xSD5THoQqN11I",
              },
              {
                quote: "Their cold-chain management is world-class. We never have to worry about sample integrity even in peak Indian summers.",
                name: "Rajesh Menon",
                role: "COO, Lifeline Hospitals",
                img: "https://lh3.googleusercontent.com/aida-public/AB6AXuAjsqIM80BCpuT3z0jD5HgC8uOEDNTbqxvu0a7AwRoL7LJjEYw2u6zEXTcxvfBAqYAkkuCJI76x34h5koZqCexp7ApmJPrhnA1X3OO7V4rhJG-iuWrOsFaDdfxIKMXYuBqt0XJkOtw-uoSKYnzC3ILI5zTaLYGZeS9T54iPv-R-77ezhyDoLvD_RP41IIUBMlnYWvJ16ErS823r8pRjcNU1RcCb-n4lRtVDACyOB8eFoH1h9wllGnoXDzO8bOH9iFRqpww4KlTbdLg",
              },
              {
                quote: "The API integration was effortless. It feels like an extension of our own lab staff rather than a vendor service.",
                name: "Amit Shrivastav",
                role: "Operations Head, CarePlus Lab",
                img: "https://lh3.googleusercontent.com/aida-public/AB6AXuCincl8bjijhD82izLkM-HGtiz2r1DplyFuuKd-q_yTXyr7Oe64lc7B8DJrEyqa_HC8rwf12XETKsSMSMmGqhGnI-SA00Nj0x0Ln--Y87amWgnLd2Bxk85Z6g8AceQmh9h4JcpP7En7R36WcRyU_JxIZfdS_siU3fqyaDLhKr3CXaYh-Fr652q9JnsPiyHH7f6InItrsbNrlUCUKFAtb6CTvUuGvbDXLN2v2M5Mqzg8b1-rNWj1iku1JNOlTGO-w2dLaZ5xoZmr8lA",
              },
            ].map((t) => (
              <div key={t.name} className="shrink-0 w-[300px] md:w-[400px] snap-center bg-background-light p-8 rounded-2xl border border-slate-100">
                <div className="flex gap-1 mb-4">
                  {[...Array(5)].map((_, i) => (
                    <span key={i} className="material-symbols-outlined text-primary text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                  ))}
                </div>
                <p className="text-slate-600 italic mb-6">&ldquo;{t.quote}&rdquo;</p>
                <div className="flex items-center gap-4">
                  <div
                    className="size-10 rounded-full bg-slate-200 bg-cover"
                    style={{ backgroundImage: `url('${t.img}')` }}
                  ></div>
                  <div>
                    <p className="font-bold text-navy-accent text-sm">{t.name}</p>
                    <p className="text-slate-500 text-xs">{t.role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-center gap-2 mt-8">
            <div className="size-2 rounded-full bg-primary"></div>
            <div className="size-2 rounded-full bg-slate-300"></div>
            <div className="size-2 rounded-full bg-slate-300"></div>
          </div>
        </div>
      </section>

      {/* Navy CTA Section */}
      <section className="px-4 py-16 bg-navy text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-5xl font-black mb-6 leading-tight">Ready to scale your lab operations?</h2>
          <p className="text-slate-400 text-lg mb-10 max-w-2xl mx-auto">
            Join 200+ lab partners across India who trust Prick &amp; Care for their phlebotomy needs.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link href="/request-demo" className="bg-primary text-navy-accent font-bold py-4 px-10 rounded-xl text-lg hover:scale-105 transition-transform">
              Get Started Now
            </Link>
            <Link href="/contact" className="border border-slate-700 bg-white/5 font-bold py-4 px-10 rounded-xl text-lg hover:bg-white/10 transition-colors">
              Contact Sales
            </Link>
          </div>
          <p className="mt-8 text-slate-500 text-sm">Free consultation • No setup fee for first 10 labs/month</p>
        </div>
      </section>

      {/* Mobile Sticky Action */}
      <div className="md:hidden fixed bottom-16 inset-x-4 z-40">
        <Link
          href="/request-demo"
          className="w-full bg-primary text-navy-accent font-black py-4 rounded-xl shadow-2xl flex items-center justify-center gap-3"
        >
          <span className="material-symbols-outlined">event_available</span>
          Book a Demo
        </Link>
      </div>
    </>
  );
}
