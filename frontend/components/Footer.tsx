"use client";

import Link from "next/link";
import { Terminal, Shield, Cpu, ExternalLink } from "lucide-react";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-white/5 bg-slate-950/20 py-12 text-slate-500">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          {/* Logo & Lab Info */}
          <div className="space-y-4">
            <Link href="/" className="flex items-center gap-2">
              <Terminal className="h-4.5 w-4.5 text-cyan-400" />
              <span className="font-bold text-slate-200">Anamnesis-AI</span>
            </Link>
            <p className="text-xs font-light leading-6 text-slate-400">
              An AI-powered Alternate Reality Research Laboratory simulating multi-agent socio-economic and climate trajectories.
            </p>
            <div className="flex items-center gap-2 pt-2 text-[10px] uppercase font-bold tracking-wider text-slate-500">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              All Systems Operational
            </div>
          </div>

          {/* Platform Links */}
          <div>
            <h4 className="mb-4 text-xs font-bold uppercase tracking-wider text-slate-300">Workspace</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/simulation" className="hover:text-cyan-400 transition-colors">Run Simulation</Link>
              </li>
              <li>
                <Link href="/library" className="hover:text-cyan-400 transition-colors">Scenario Library</Link>
              </li>
              <li>
                <Link href="/architecture" className="hover:text-cyan-400 transition-colors">Agent Pipeline</Link>
              </li>
              <li>
                <Link href="/roadmap" className="hover:text-cyan-400 transition-colors">Roadmap</Link>
              </li>
            </ul>
          </div>

          {/* Research & Docs */}
          <div>
            <h4 className="mb-4 text-xs font-bold uppercase tracking-wider text-slate-300">Research</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/methodology" className="hover:text-cyan-400 transition-colors">Methodology</Link>
              </li>
              <li>
                <Link href="/docs" className="hover:text-cyan-400 transition-colors">API & Documentation</Link>
              </li>
              <li>
                <Link href="/about" className="hover:text-cyan-400 transition-colors">About Platform</Link>
              </li>
            </ul>
          </div>

          {/* GitHub & Team */}
          <div>
            <h4 className="mb-4 text-xs font-bold uppercase tracking-wider text-slate-300">Organization</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/contact" className="hover:text-cyan-400 transition-colors">Meet the Team</Link>
              </li>
              <li>
                <a href="https://github.com/Anamnesis-AI-Org/Anamnesis-AI" target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-cyan-400 transition-colors">
                  GitHub Repository <ExternalLink className="h-3 w-3" />
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-white/5 pt-8 text-[11px] font-light text-slate-600">
          <div className="flex items-center gap-2">
            <Shield className="h-3.5 w-3.5" />
            <span>Secured Multi-Agent Alternate Reality Engine</span>
          </div>
          <div>
            © {currentYear} Anamnesis-AI. Handcrafted for premium simulation.
          </div>
        </div>
      </div>
    </footer>
  );
}
