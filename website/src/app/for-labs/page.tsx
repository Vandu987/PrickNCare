import Link from "next/link";

export const metadata = { title: "For Labs & Partners - Prick & Care" };

export default function ForLabsPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative px-4 pt-8 pb-12 md:py-20 overflow-hidden">
        <div className="relative z-10 text-center flex flex-col items-center gap-6 max-w-3xl mx-auto">
          <span className="bg-primary/20 text-emerald-700 text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-widest border border-primary/30">
            #1 Phlebotomy Network
          </span>
          <h2 className="text-slate-900 text-4xl md:text-5xl font-black leading-[1.1] tracking-tight">
            Partner With India&apos;s Leading Phlebotomy Network
          </h2>
          <p className="text-slate-600 text-base md:text-lg font-medium max-w-md">
            Scale your sample collection with 99.9% reliability and seamless LIMS integration.
          </p>
          <div className="flex flex-col sm:flex-row w-full sm:w-auto gap-3 mt-4">
            <Link
              href="/request-demo"
              className="w-full sm:w-auto bg-primary hover:bg-primary/90 text-background-dark h-14 rounded-xl font-bold text-lg shadow-lg shadow-primary/20 flex items-center justify-center px-8"
            >
              Start Your Free Pilot
            </Link>
          </div>
          <p className="text-xs text-slate-500 flex items-center justify-center gap-1">
            <span className="material-symbols-outlined text-sm text-primary">verified</span>
            Trusted by 200+ NABL Labs
          </p>
        </div>
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-64 h-64 bg-primary/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-64 h-64 bg-primary/5 rounded-full blur-3xl"></div>
      </section>

      {/* Problem-Solution */}
      <section className="px-4 py-12 bg-white rounded-t-[2.5rem] shadow-2xl">
        <div className="max-w-4xl mx-auto">
          <h3 className="text-slate-900 text-2xl font-bold mb-8 text-center">The Challenge vs. The Solution</h3>
          <div className="space-y-6">
            {[
              { challenge: "Unpredictable staffing costs & high attrition rates", solution: "Access to 5,000+ certified phlebotomists on demand" },
              { challenge: "Logistics delays and sample integrity issues", solution: "90-min TAT with real-time temperature tracking" },
            ].map((row, i) => (
              <div key={i} className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-slate-100 p-4 rounded-xl border-l-4 border-red-400">
                  <p className="text-xs font-bold text-slate-500 uppercase mb-1">Lab Challenge</p>
                  <p className="text-sm font-semibold text-slate-700">{row.challenge}</p>
                </div>
                <div className="bg-primary/10 p-4 rounded-xl border-l-4 border-primary">
                  <p className="text-xs font-bold text-primary uppercase mb-1">Our Solution</p>
                  <p className="text-sm font-semibold text-slate-900">{row.solution}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Partnership Models */}
      <section className="py-12 px-4 overflow-hidden max-w-7xl mx-auto">
        <h3 className="text-slate-900 text-2xl font-bold mb-6">Partnership Models</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-6 rounded-2xl shadow-md border border-slate-100">
            <div className="w-12 h-12 bg-primary/20 rounded-xl flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-emerald-600">group</span>
            </div>
            <h4 className="text-xl font-bold mb-2">Dedicated Team</h4>
            <p className="text-slate-500 text-sm leading-relaxed">Permanent workforce assigned exclusively to your high-volume collection centers.</p>
          </div>
          <div className="bg-background-dark text-white p-6 rounded-2xl shadow-xl border border-primary/30">
            <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-background-dark">payments</span>
            </div>
            <h4 className="text-xl font-bold mb-2 text-primary">Pay Per Collection</h4>
            <p className="text-slate-300 text-sm leading-relaxed">Variable cost model. Pay only when a sample is successfully collected. No overheads.</p>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-md border border-slate-100">
            <div className="w-12 h-12 bg-primary/20 rounded-xl flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-emerald-600">shuffle</span>
            </div>
            <h4 className="text-xl font-bold mb-2">Hybrid Model</h4>
            <p className="text-slate-500 text-sm leading-relaxed">Flexible scaling: Fixed staff for baseline demand + on-demand staff for peak hours.</p>
          </div>
        </div>
      </section>

      {/* LIMS Integration */}
      <section className="px-4 py-12 bg-slate-900 md:rounded-3xl md:mx-4 lg:mx-auto lg:max-w-5xl text-white">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h3 className="text-2xl font-bold mb-2">Seamless LIMS Integration</h3>
            <p className="text-slate-400 text-sm">Connect your existing lab software in minutes via our robust API suite.</p>
          </div>
          <div className="bg-black/50 rounded-xl border border-slate-700 p-4 font-mono text-[10px] md:text-xs overflow-hidden shadow-inner">
            <div className="flex items-center gap-1.5 mb-3">
              <div className="w-2 h-2 rounded-full bg-red-500"></div>
              <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              <span className="ml-2 text-slate-500">GET /api/v1/collection-status</span>
            </div>
            <pre className="text-emerald-400">{`{
  "status": "success",
  "order_id": "PC-88291",
  "phleb_id": "PH-007",
  "location": {
    "lat": 12.9716,
    "lng": 77.5946
  },
  "tracking": "In-Transit"
}`}</pre>
          </div>
          <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: "code", label: "JSON API" },
              { icon: "hub", label: "HL7 v2 / v3" },
              { icon: "database", label: "FHIR Ready" },
              { icon: "lock", label: "HIPAA Comp." },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2 bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                <span className="material-symbols-outlined text-primary">{item.icon}</span>
                <span className="text-sm font-semibold">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-16 px-4 max-w-4xl mx-auto">
        <h3 className="text-2xl font-bold mb-8 text-center">Transparent Pricing</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Starter */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 relative">
            <h4 className="text-lg font-bold mb-4">Starter</h4>
            <div className="mb-4">
              <span className="text-3xl font-black">₹499</span>
              <span className="text-slate-500 font-medium">/sample</span>
            </div>
            <ul className="space-y-3 mb-6">
              <li className="flex items-center gap-2 text-sm text-slate-600">
                <span className="material-symbols-outlined text-primary text-lg">check_circle</span>
                Up to 50 samples/month
              </li>
              <li className="flex items-center gap-2 text-sm text-slate-600">
                <span className="material-symbols-outlined text-primary text-lg">check_circle</span>
                90-min turnaround time
              </li>
            </ul>
            <button className="w-full py-3 rounded-xl border-2 border-slate-200 font-bold text-sm">Select Starter</button>
          </div>
          {/* Growth */}
          <div className="bg-white p-6 rounded-2xl border-2 border-primary relative shadow-xl md:scale-105 z-10">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-background-dark text-[10px] font-black px-4 py-1 rounded-full uppercase">Most Popular</div>
            <h4 className="text-lg font-bold mb-4">Growth</h4>
            <div className="mb-4">
              <span className="text-3xl font-black">₹349</span>
              <span className="text-slate-500 font-medium">/sample</span>
            </div>
            <ul className="space-y-3 mb-6">
              <li className="flex items-center gap-2 text-sm font-semibold">
                <span className="material-symbols-outlined text-primary text-lg">check_circle</span>
                Unlimited samples
              </li>
              <li className="flex items-center gap-2 text-sm font-semibold">
                <span className="material-symbols-outlined text-primary text-lg">check_circle</span>
                Dedicated LIMS support
              </li>
              <li className="flex items-center gap-2 text-sm font-semibold">
                <span className="material-symbols-outlined text-primary text-lg">check_circle</span>
                99.9% SLA Guarantee
              </li>
            </ul>
            <button className="w-full py-3 rounded-xl bg-primary text-background-dark font-bold text-sm">Select Growth</button>
          </div>
          {/* Enterprise */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200">
            <h4 className="text-lg font-bold mb-4">Enterprise</h4>
            <div className="mb-4">
              <span className="text-3xl font-black">Custom</span>
            </div>
            <ul className="space-y-3 mb-6">
              <li className="flex items-center gap-2 text-sm text-slate-600">
                <span className="material-symbols-outlined text-primary text-lg">check_circle</span>
                Fixed personnel onsite
              </li>
              <li className="flex items-center gap-2 text-sm text-slate-600">
                <span className="material-symbols-outlined text-primary text-lg">check_circle</span>
                White-label application
              </li>
            </ul>
            <Link href="/contact" className="block w-full py-3 rounded-xl border-2 border-slate-200 font-bold text-sm text-center">Contact Sales</Link>
          </div>
        </div>
      </section>

      {/* Lead Gen Form */}
      <section className="px-4 py-16 bg-background-light">
        <div className="bg-white p-8 rounded-[2rem] shadow-2xl border border-slate-100 max-w-lg mx-auto">
          <div className="text-center mb-8">
            <h3 className="text-2xl font-black mb-2">Start Your Free Pilot</h3>
            <p className="text-slate-500 text-sm">Experience the difference for 7 days with zero commitment.</p>
          </div>
          <form className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1.5 ml-1">Full Name</label>
              <input className="w-full bg-slate-50 border-none rounded-xl h-14 px-4 text-sm focus:ring-2 focus:ring-primary" placeholder="John Doe" type="text" />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1.5 ml-1">Lab/Hospital Name</label>
              <input className="w-full bg-slate-50 border-none rounded-xl h-14 px-4 text-sm focus:ring-2 focus:ring-primary" placeholder="Apollo Diagnostics" type="text" />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1.5 ml-1">Monthly Sample Volume</label>
              <select className="w-full bg-slate-50 border-none rounded-xl h-14 px-4 text-sm focus:ring-2 focus:ring-primary">
                <option>Under 1,000</option>
                <option>1,000 - 5,000</option>
                <option>5,000 - 20,000</option>
                <option>20,000+</option>
              </select>
            </div>
            <button className="w-full bg-primary text-background-dark font-black text-lg h-14 rounded-xl shadow-lg shadow-primary/20 mt-4 active:scale-95 transition-transform" type="submit">
              Get Free Quote
            </button>
          </form>
          <p className="text-[10px] text-center text-slate-400 mt-6">By clicking, you agree to our Terms of Service and Privacy Policy. No credit card required.</p>
        </div>
      </section>
    </>
  );
}
