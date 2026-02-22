export const metadata = { title: "Careers - Prick & Care" };

export default function CareersPage() {
  return (
    <>
      {/* Hero */}
      <div className="relative flex min-h-[420px] flex-col gap-6 bg-cover bg-center bg-no-repeat items-center justify-center p-6 text-center rounded-xl mx-4 mt-4 overflow-hidden"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.7)), url('https://lh3.googleusercontent.com/aida-public/AB6AXuB659C-PAEHmbRajSg4MlDzJokJ3ClAwjClFO2QWdY_mA4_LIc8Meo_8meH4pN89663t3GnZfLXkCyln-Yansr6VkxLyJKPPB0u8Ur02Xrf3M62atMdP5RUegTD5hkFm60DDYEc2OA2c9dF-WExgV7hMYiV759b_qXfctvk-R63G7Yj89GSYHLpVLGFB97o560pfsJNTS9fpjQ2tAG2VzZvAfve8kTkAi81GXQbsbu3tzGK5IJEcWnJkRlyaNOGkuj5rOG8Q8Ovwoc')",
        }}
      >
        <div className="flex flex-col gap-3">
          <h1 className="text-white text-4xl md:text-5xl font-black leading-tight tracking-tight">
            Join the Prick &amp; Care Team
          </h1>
          <p className="text-slate-200 text-base font-normal max-w-md mx-auto">
            Empowering healthcare through precision and professional excellence. Start your journey with India&apos;s leading B2B phlebotomy partner.
          </p>
        </div>
        <a
          className="flex min-w-[160px] cursor-pointer items-center justify-center overflow-hidden rounded-full h-12 px-6 bg-primary text-slate-900 text-base font-bold leading-normal tracking-wide transition-transform active:scale-95"
          href="#open-positions"
        >
          View Openings
        </a>
      </div>

      {/* Why Join Us */}
      <section className="py-10 px-4 max-w-4xl mx-auto">
        <h2 className="text-slate-900 text-2xl font-extrabold leading-tight tracking-tight mb-6">Why Join Us</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: "payments", title: "Competitive Pay", desc: "Industry-leading compensation packages." },
            { icon: "school", title: "Paid Training", desc: "Continuous clinical skill development." },
            { icon: "trending_up", title: "Growth", desc: "Fast-track paths to management roles." },
            { icon: "health_and_safety", title: "Health Cover", desc: "Comprehensive insurance for your family." },
          ].map((b) => (
            <div key={b.title} className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="text-primary bg-primary/10 w-10 h-10 rounded-lg flex items-center justify-center">
                <span className="material-symbols-outlined">{b.icon}</span>
              </div>
              <div className="flex flex-col gap-1">
                <h3 className="text-slate-900 text-base font-bold">{b.title}</h3>
                <p className="text-slate-500 text-xs leading-relaxed">{b.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Open Positions */}
      <section className="py-6 px-4 bg-slate-100" id="open-positions">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-slate-900 text-2xl font-extrabold tracking-tight">Open Positions</h2>
            <span className="bg-primary/20 text-primary text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">5 Jobs</span>
          </div>
          <div className="space-y-4">
            {[
              { title: "Senior Phlebotomist", location: "Delhi NCR", salary: "₹3.5L - 5.0L PA", tags: ["Full-Time", "On-Site"] },
              { title: "Phlebotomist", location: "Mumbai", salary: "₹3.0L - 4.5L PA", tags: ["Full-Time", "On-Site"] },
              { title: "City Operations Manager", location: "Bengaluru", salary: "₹8L - 12L PA", tags: ["Management", "Hybrid"] },
              { title: "Software Engineer (L2)", location: "Remote", salary: "₹15L - 22L PA", tags: ["Tech", "Remote"] },
            ].map((job) => (
              <div key={job.title} className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col gap-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">{job.title}</h3>
                    <p className="text-sm text-slate-500 flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">location_on</span> {job.location}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-primary">{job.salary}</span>
                </div>
                <div className="flex items-center gap-2">
                  {job.tags.map((tag) => (
                    <span key={tag} className="px-2 py-1 bg-slate-100 text-[10px] font-bold rounded uppercase">{tag}</span>
                  ))}
                </div>
                <button className="w-full bg-primary text-slate-900 font-bold py-3 rounded-lg text-sm transition-colors active:bg-primary/80">Apply Now</button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Life at Prick & Care */}
      <section className="py-10 px-4 max-w-4xl mx-auto">
        <h2 className="text-slate-900 text-2xl font-extrabold tracking-tight mb-6">Life at Prick &amp; Care</h2>
        <div className="grid grid-cols-3 grid-rows-2 gap-2 h-80">
          <div
            className="col-span-2 row-span-2 rounded-xl overflow-hidden bg-slate-200 bg-cover bg-center"
            style={{
              backgroundImage:
                "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCkVKQKXXADKW6fw6uUVTVpeRmxe2h_LZYr5LcmCRWvFg2TWyK19G16aKp7KuhQVQd2IXzR8WXKJK6nAXOuwcl4etmgIQ3pHPjX-GLSEDz48x8pusUtWLpBvJcVM4liYwV2-FKAr8Bqy7pmAB_z43H1hU0jzdlymizeEZwW44hkonp9bnIs9YyNPQcAMvCC6Q0j_zLZcaY5XiiF2aGPTlpzenwdxwbXpQ5hNFWrBS_QlRoswASJMcMQhL7FIXafpZvshJJ79g0_s3o')",
            }}
          ></div>
          <div
            className="rounded-xl overflow-hidden bg-slate-200 bg-cover bg-center"
            style={{
              backgroundImage:
                "url('https://lh3.googleusercontent.com/aida-public/AB6AXuA2cxxC3DX1e-qe8KEUoqv5bR4VNQV43AqDUpmQ9NDyT-NezJLLymXwf4Y50weOc-KvZFp9_m6nUnK_98TG7nZqfIS4l1qFURhQTtaENKMNFdklcXAxSYKVMSdU_OXr53z4K4dCKrP9pli2hxi51AIvaTPPEKjDGyr7MlB0piHZDyLmoqT1H3QBGNCzvW_2WrqBU561YTSHDRIJS3Z5FUctrIshPyTFn7jDNEDXEkkrEsNU8bL9-66H4fsgJGIjxNIMvJiBwP2xARk')",
            }}
          ></div>
          <div
            className="rounded-xl overflow-hidden bg-slate-200 bg-cover bg-center"
            style={{
              backgroundImage:
                "url('https://lh3.googleusercontent.com/aida-public/AB6AXuB15V7WX4GgF8LzgbmWA4ysxZ_9K45uVIBk99mv1Uf0TkcSYa1-yRF1VbeYoS5XoAcpOIZoPkmeao5jIJzPYiyxIntd2taCBNbF4GuvL0AFWQ3VRnFU9-DR8xBBtetiUSGJolwNuVysmlQfqR79LdBI77kLE_jFFKxnzP6G2he0dikGaXLBvXD4FrtR_KxeLjWPGi_EIMp2dTkqZ0NUCj0uT69Fih2ksa_UptWZLC4mKU7mS9CvA6jNbK-_i6IQqcHfI8Nfk6W9VZk')",
            }}
          ></div>
        </div>
      </section>

      {/* Application Form */}
      <section className="py-10 px-4 bg-white rounded-t-[2rem] shadow-2xl border-t border-slate-200">
        <div className="max-w-md mx-auto">
          <h2 className="text-2xl font-extrabold text-slate-900 mb-2">Send us your resume</h2>
          <p className="text-slate-500 text-sm mb-8">Can&apos;t find a perfect role? Drop your CV and we&apos;ll reach out when we have an opening.</p>
          <form className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Full Name</label>
              <input className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:ring-2 focus:ring-primary focus:border-transparent outline-none" placeholder="John Doe" type="text" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Email Address</label>
              <input className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:ring-2 focus:ring-primary focus:border-transparent outline-none" placeholder="john@example.com" type="email" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Phone Number</label>
              <input className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:ring-2 focus:ring-primary focus:border-transparent outline-none" placeholder="+91 98765 43210" type="tel" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Desired Position</label>
              <select className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-slate-50 text-slate-900 focus:ring-2 focus:ring-primary focus:border-transparent outline-none">
                <option>Phlebotomist</option>
                <option>Operations</option>
                <option>Tech / Engineering</option>
                <option>Sales / Marketing</option>
                <option>Other</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Upload Resume</label>
              <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 flex flex-col items-center justify-center bg-slate-50 cursor-pointer hover:border-primary transition-colors">
                <span className="material-symbols-outlined text-slate-400 text-4xl mb-2">cloud_upload</span>
                <p className="text-sm text-slate-500 font-medium">Tap to upload PDF or DOC</p>
              </div>
            </div>
            <button className="w-full bg-primary text-slate-900 font-black py-4 rounded-xl text-lg shadow-lg active:scale-95 transition-transform mt-4" type="submit">
              Submit Application
            </button>
          </form>
        </div>
      </section>
    </>
  );
}
