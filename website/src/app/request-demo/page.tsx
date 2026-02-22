import Link from "next/link";

export const metadata = { title: "Request a Demo - Prick & Care" };

export default function RequestDemoPage() {
  return (
    <>
      {/* Hero Section */}
      <div className="bg-navy-deep p-6 md:p-12 text-white overflow-hidden relative">
        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full -mr-16 -mt-16 blur-3xl"></div>
        <div className="relative z-10 max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold leading-tight tracking-tight mb-4">See Prick &amp; Care in Action</h1>
            <p className="text-primary/90 font-medium mb-6">Empowering diagnostic labs and hospitals with next-gen phlebotomy logistics.</p>
            {/* Benefit Items */}
            <div className="space-y-4 mb-8">
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined text-primary text-xl">monitoring</span>
                <p className="text-slate-100 text-sm leading-snug">Real-time tracking of all samples with integrated temperature monitoring.</p>
              </div>
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined text-primary text-xl">payments</span>
                <p className="text-slate-100 text-sm leading-snug">Custom pricing structures optimized for high-volume diagnostic facilities.</p>
              </div>
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined text-primary text-xl">verified_user</span>
                <p className="text-slate-100 text-sm leading-snug">Hospital-grade reliability &amp; HIPAA-compliant data security at every step.</p>
              </div>
            </div>
            {/* Testimonial Mini-Card */}
            <div className="bg-white/5 backdrop-blur-md rounded-xl p-4 border border-white/10">
              <p className="text-slate-200 italic text-sm mb-3">&ldquo;Prick &amp; Care transformed our outpatient workflow completely. Our turnaround times improved by 40%.&rdquo;</p>
              <div className="flex items-center gap-3">
                <div className="size-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <span className="material-symbols-outlined text-primary text-lg">person</span>
                </div>
                <div>
                  <p className="text-white text-xs font-bold">Director of Operations</p>
                  <p className="text-slate-400 text-[10px]">City General Hospital</p>
                </div>
              </div>
            </div>
          </div>

          {/* Form (desktop: side by side) */}
          <div className="hidden lg:block"></div>
        </div>
      </div>

      {/* Form Section */}
      <div className="flex-1 bg-white rounded-t-3xl -mt-6 relative z-20 px-6 pt-8 pb-12 shadow-2xl">
        <div className="max-w-lg mx-auto">
          <div className="mb-8">
            <h3 className="text-2xl font-bold text-slate-900">Get Started</h3>
            <p className="text-slate-500 text-sm">Fill out the form below and our team will contact you within 24 hours.</p>
          </div>
          <form className="space-y-5">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-slate-700 ml-1">Full Name</label>
              <input className="w-full rounded-lg border-slate-200 bg-slate-50 text-slate-900 focus:border-primary focus:ring-primary transition-all p-3 text-base" placeholder="Dr. Sarah Jenkins" type="text" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-slate-700 ml-1">Work Email</label>
              <input className="w-full rounded-lg border-slate-200 bg-slate-50 text-slate-900 focus:border-primary focus:ring-primary transition-all p-3 text-base" placeholder="s.jenkins@hospital.org" type="email" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-slate-700 ml-1">Phone Number</label>
              <input className="w-full rounded-lg border-slate-200 bg-slate-50 text-slate-900 focus:border-primary focus:ring-primary transition-all p-3 text-base" placeholder="+1 (555) 000-0000" type="tel" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-slate-700 ml-1">Lab / Hospital Name</label>
              <input className="w-full rounded-lg border-slate-200 bg-slate-50 text-slate-900 focus:border-primary focus:ring-primary transition-all p-3 text-base" placeholder="Central Diagnostic Lab" type="text" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-slate-700 ml-1">City</label>
              <input className="w-full rounded-lg border-slate-200 bg-slate-50 text-slate-900 focus:border-primary focus:ring-primary transition-all p-3 text-base" placeholder="New York, NY" type="text" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-slate-700 ml-1">Monthly Sample Volume</label>
              <div className="relative">
                <select className="w-full appearance-none rounded-lg border-slate-200 bg-slate-50 text-slate-900 focus:border-primary focus:ring-primary transition-all p-3 pr-10 text-base">
                  <option disabled value="">Select volume range</option>
                  <option value="0-500">0 - 500 samples</option>
                  <option value="500-2000">500 - 2,000 samples</option>
                  <option value="2000-5000">2,000 - 5,000 samples</option>
                  <option value="5000+">5,000+ samples</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-500">
                  <span className="material-symbols-outlined">expand_more</span>
                </div>
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-slate-700 ml-1">Specific Requirements</label>
              <textarea className="w-full rounded-lg border-slate-200 bg-slate-50 text-slate-900 focus:border-primary focus:ring-primary transition-all p-3 text-base resize-none" placeholder="Tell us about your current challenges..." rows={3}></textarea>
            </div>
            <div className="pt-4">
              <button className="w-full bg-primary hover:bg-primary/90 text-navy-deep font-bold py-4 rounded-xl shadow-lg shadow-primary/20 transition-all flex items-center justify-center gap-2 active:scale-[0.98]" type="submit">
                <span>Schedule My Demo</span>
                <span className="material-symbols-outlined">calendar_today</span>
              </button>
              <p className="text-center text-[11px] text-slate-400 mt-4 leading-relaxed px-4">
                By clicking, you agree to our Terms of Service and Privacy Policy. We value your data security.
              </p>
            </div>
          </form>
        </div>
      </div>

      {/* Trust Logos */}
      <div className="bg-white px-6 pb-12 border-t border-slate-100">
        <p className="text-center text-[10px] uppercase tracking-widest text-slate-400 mb-6 mt-8 font-bold">Trusted by leading institutions</p>
        <div className="flex justify-center items-center gap-8 opacity-40 grayscale">
          {[
            "https://lh3.googleusercontent.com/aida-public/AB6AXuCOiIJwctF8Xj5RlsP1xCem7wuS-5mmOEuMk9bqg06LCEOb6QkyvhSQKH8zaE9CR3Dt40sj7H2qTfNqOoZWczFzrifZQC3aNBcRa764W8kdNqRy7h0pYTt06vZ1jMUvdSkiB89haSAv6jXhuiIzaM1z1cXTO49YvUwDU20xZ6celw7jDG7WIgi1-VyGpBidZ5hUyQQjAmVhRVT_jISJx8iVMAE4mqY1gXS7QNeo4juVaYKLnC-_6AmKy9csVRuB4c6fN2gA4tH7gBU",
            "https://lh3.googleusercontent.com/aida-public/AB6AXuBTuEhVq-vUV-D4JGlJ1kY7cwsI4qvglscXeyyaDkx8mP4M-GaT4qmDyyjhjIeDEA8XSqKpnAaH8r6mqzeBJ2j6BhyNd6prLnIay16naM3u1rAe0GZHWDv13FC3TswGLcPXSlp9CjuqqE2JnZXO9dGz8ehd0RcneLhQp6oWG4QOXO2Q_jeVWplqNLD8hfhLNpHcoxewbiBTZwc1i6QhyNdNqo9YNwJySk39Y-l66knRfgwqACBC3-CbMeBnORQFlsoNlgjAGuohNA4",
            "https://lh3.googleusercontent.com/aida-public/AB6AXuDvTBZx-1-Kyc8Tz3bABnhxFPTuBp5Ka6XmS74Mx3Lm9xKoTFzMN4ERc7rMJ41YlHTsKmW-de42mIYgKtd2kgyE-dg9xKAg99OHj-1styoIZi18LfidZJEX8qCNXDV5Lsewte-VT81bjiDxuu1QDI56qcrpGT8c9pbU1lfsMO-QVpEEScqflINYAM1ojfWouIXpH6VvtkkkRymLnsZVpzPNzaCHVrrccQupbP-9XlufAfhxIlHxg93S05XDeSqW99qGxq9yJOx-f5k",
          ].map((src, i) => (
            <img key={i} alt={`Partner Logo ${i + 1}`} className="h-6" src={src} />
          ))}
        </div>
      </div>
    </>
  );
}
