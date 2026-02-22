import Link from "next/link";
import Image from "next/image";

export default function Footer() {
  return (
    <footer className="bg-white border-t border-slate-100 pt-16 pb-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-10 mb-16">
          <div className="col-span-2">
            <div className="mb-6">
              <Image
                src="/logo.jpeg"
                alt="Prick & Care"
                width={180}
                height={64}
                className="h-14 w-auto object-contain"
              />
            </div>
            <p className="text-slate-500 text-sm leading-relaxed max-w-xs mb-6">
              Empowering diagnostic labs and hospitals with technology-driven, reliable phlebotomy and logistics solutions.
            </p>
            <div className="flex gap-4">
              <a className="size-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 hover:text-primary transition-colors" href="#">
                <span className="material-symbols-outlined">share</span>
              </a>
              <a className="size-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 hover:text-primary transition-colors" href="#">
                <span className="material-symbols-outlined">chat</span>
              </a>
              <a className="size-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 hover:text-primary transition-colors" href="#">
                <span className="material-symbols-outlined">alternate_email</span>
              </a>
            </div>
          </div>
          <div>
            <h6 className="font-bold text-navy-accent mb-6">Services</h6>
            <ul className="space-y-4 text-sm text-slate-500">
              <li><Link className="hover:text-primary" href="/services">Home Collection</Link></li>
              <li><Link className="hover:text-primary" href="/services">Corporate Camps</Link></li>
              <li><Link className="hover:text-primary" href="/services">Lab Logistics</Link></li>
              <li><Link className="hover:text-primary" href="/services">LIMS Integration</Link></li>
            </ul>
          </div>
          <div>
            <h6 className="font-bold text-navy-accent mb-6">Company</h6>
            <ul className="space-y-4 text-sm text-slate-500">
              <li><Link className="hover:text-primary" href="/about">About Us</Link></li>
              <li><Link className="hover:text-primary" href="/careers">Careers</Link></li>
              <li><a className="hover:text-primary" href="#">Press Kit</a></li>
              <li><Link className="hover:text-primary" href="/contact">Contact</Link></li>
            </ul>
          </div>
          <div>
            <h6 className="font-bold text-navy-accent mb-6">Legal</h6>
            <ul className="space-y-4 text-sm text-slate-500">
              <li><a className="hover:text-primary" href="#">Privacy Policy</a></li>
              <li><a className="hover:text-primary" href="#">Terms of Service</a></li>
              <li><a className="hover:text-primary" href="#">Compliance</a></li>
            </ul>
          </div>
        </div>
        <div className="pt-8 border-t border-slate-100 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-slate-400">
          <p>© 2024 Prick &amp; Care Phlebotomy Services Pvt. Ltd. All rights reserved.</p>
          <div className="flex gap-6">
            <span className="flex items-center gap-1"><span className="material-symbols-outlined text-xs">public</span> India</span>
            <a className="flex items-center gap-1 hover:text-primary transition-colors" href="tel:+919876543210">
              <span className="material-symbols-outlined text-xs">call</span> +91 98765 43210
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
