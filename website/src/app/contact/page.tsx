export const metadata = { title: "Contact Us - Prick & Care" };

export default function ContactPage() {
  return (
    <>
      {/* Hero */}
      <section className="px-6 py-10 bg-gradient-to-b from-primary/10 to-transparent">
        <div className="max-w-2xl mx-auto space-y-3">
          <span className="inline-block px-3 py-1 text-xs font-bold tracking-wider uppercase bg-primary/20 text-slate-800 rounded-full">Support Center</span>
          <h2 className="text-4xl md:text-5xl font-black tracking-tight leading-tight">Get In Touch</h2>
          <p className="text-slate-600 text-base leading-relaxed">
            Our team of phlebotomy experts is here to support your diagnostic lab or hospital operations.
          </p>
        </div>
      </section>

      {/* Main Form */}
      <section className="px-6 py-4 max-w-2xl mx-auto">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-primary/5">
          <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">mail</span>
            Send Us a Message
          </h3>
          <form className="space-y-4">
            <div>
              <label className="block text-sm font-semibold mb-1.5 ml-1">Full Name</label>
              <input className="w-full h-12 px-4 rounded-lg border-slate-200 bg-slate-50 focus:ring-2 focus:ring-primary focus:border-primary transition-all" placeholder="John Doe" type="text" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold mb-1.5 ml-1">Work Email</label>
                <input className="w-full h-12 px-4 rounded-lg border-slate-200 bg-slate-50 focus:ring-2 focus:ring-primary focus:border-primary transition-all" placeholder="name@lab.com" type="email" />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-1.5 ml-1">Phone Number</label>
                <input className="w-full h-12 px-4 rounded-lg border-slate-200 bg-slate-50 focus:ring-2 focus:ring-primary focus:border-primary transition-all" placeholder="+91 98765 43210" type="tel" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1.5 ml-1">Lab / Hospital Name</label>
              <input className="w-full h-12 px-4 rounded-lg border-slate-200 bg-slate-50 focus:ring-2 focus:ring-primary focus:border-primary transition-all" placeholder="City Diagnostics Center" type="text" />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1.5 ml-1">City</label>
              <input className="w-full h-12 px-4 rounded-lg border-slate-200 bg-slate-50 focus:ring-2 focus:ring-primary focus:border-primary transition-all" placeholder="New Delhi" type="text" />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1.5 ml-1">Subject</label>
              <select className="w-full h-12 px-4 rounded-lg border-slate-200 bg-slate-50 focus:ring-2 focus:ring-primary focus:border-primary transition-all">
                <option>Partnership Inquiry</option>
                <option>Technical Support</option>
                <option>Billing Question</option>
                <option>Career Opportunity</option>
                <option>Other</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1.5 ml-1">Your Message</label>
              <textarea className="w-full px-4 py-3 rounded-lg border-slate-200 bg-slate-50 focus:ring-2 focus:ring-primary focus:border-primary transition-all" placeholder="How can we help your facility today?" rows={4}></textarea>
            </div>
            <button className="w-full bg-primary text-slate-900 font-bold py-4 rounded-xl shadow-lg shadow-primary/20 active:scale-[0.98] transition-transform flex items-center justify-center gap-2" type="submit">
              Send Message
              <span className="material-symbols-outlined">send</span>
            </button>
          </form>
        </div>
      </section>

      {/* Contact Info & Map */}
      <section className="px-6 py-10 max-w-2xl mx-auto space-y-8">
        <div className="space-y-6">
          <h3 className="text-2xl font-black tracking-tight">Our Headquarters</h3>
          <div className="relative w-full h-64 rounded-xl overflow-hidden border-4 border-white shadow-xl">
            <div
              className="w-full h-full bg-cover bg-center"
              style={{
                backgroundImage:
                  "url('https://lh3.googleusercontent.com/aida-public/AB6AXuBX--Rw5t8_yAxPvVTMdQKTOkFor2s4PtuKWWizWFQPDL4k_nxz6eriuLliZvSp5AlILlDoeKlKyL3LJsgTJBJIHcbHQoNbVZDNjab0h2axZHE4368dsWxCF3sabvtZsGxIEKuAU9kQqw2-1khdOoc-O8IhfJ-fJyjpbJtL50-y4ZT9989kA2MJx4hw7sQJRp3PchSqd95GFmuF8Z5sM99Sn06XVKnOxu24cKJPzg2NAH2ZmpsgJ2ez2KsyLR55E32U4YJI-_Q-8u8')",
              }}
            ></div>
            <div className="absolute inset-0 bg-primary/10 flex items-center justify-center">
              <div className="bg-white p-3 rounded-full shadow-2xl animate-bounce">
                <span className="material-symbols-outlined text-primary text-3xl">location_on</span>
              </div>
            </div>
            <div className="absolute bottom-4 left-4 right-4 bg-white/90 backdrop-blur p-3 rounded-lg flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Delhi NCR Hub</span>
              <a className="text-primary text-sm font-bold flex items-center gap-1" href="#">
                Open Maps <span className="material-symbols-outlined text-sm">open_in_new</span>
              </a>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4">
            {[
              { icon: "apartment", title: "Address", desc: "Sector 62, Electronic City, Noida, UP - 201301, India", sub: null },
              { icon: "call", title: "Phone", desc: "+91 (120) 456-7890", sub: "Mon-Sat, 9 AM - 7 PM" },
              { icon: "alternate_email", title: "Email", desc: "support@prickandcare.com", sub: null },
            ].map((info) => (
              <div key={info.title} className="flex items-start gap-4 p-4 bg-white rounded-xl border border-primary/5">
                <div className="bg-primary/10 p-2 rounded-lg text-primary">
                  <span className="material-symbols-outlined">{info.icon}</span>
                </div>
                <div>
                  <h4 className="font-bold">{info.title}</h4>
                  <p className="text-sm text-slate-600">{info.desc}</p>
                  {info.sub && <p className="text-xs text-slate-400">{info.sub}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Quick Departments */}
      <section className="px-6 py-10 bg-slate-100">
        <div className="max-w-2xl mx-auto">
          <h3 className="text-xl font-bold mb-6">Quick Departments</h3>
          <div className="space-y-4">
            {[
              { icon: "handshake", title: "Partnerships", desc: "For lab & hospital networks" },
              { icon: "work", title: "Careers", desc: "Join our phlebotomy team" },
              { icon: "medical_services", title: "Clinical Support", desc: "For urgent medical queries" },
            ].map((dept) => (
              <div key={dept.title} className="flex items-center justify-between p-5 bg-white rounded-xl shadow-sm">
                <div className="flex items-center gap-4">
                  <span className="material-symbols-outlined text-primary">{dept.icon}</span>
                  <div>
                    <p className="font-bold">{dept.title}</p>
                    <p className="text-xs text-slate-500">{dept.desc}</p>
                  </div>
                </div>
                <span className="material-symbols-outlined text-slate-400">chevron_right</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
