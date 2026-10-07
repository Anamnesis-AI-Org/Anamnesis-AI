"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { 
  Terminal, Activity, BookOpen, Layers, Milestone, Compass, Users, Home, Search 
} from "lucide-react";
import CommandPalette from "./CommandPalette";
import SoundToggle from "./SoundToggle";

export default function Navbar() {
  const pathname = usePathname();
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);

  // Global key listener for CMD+K or CTRL+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const links = [
    { href: "/", label: "Home", icon: Home },
    { href: "/simulation", label: "Simulation", icon: Activity },
    { href: "/library", label: "Library", icon: Compass },
    { href: "/methodology", label: "Methodology", icon: BookOpen },
    { href: "/architecture", label: "Architecture", icon: Layers },
    { href: "/docs", label: "Docs", icon: Terminal },
    { href: "/roadmap", label: "Roadmap", icon: Milestone },
    { href: "/contact", label: "Team", icon: Users }
  ];

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-black/55 backdrop-blur-md transition-all duration-300">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <div className="flex items-center">
              <Link href="/" className="flex items-center gap-2 group">
                <div className="relative flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg border border-cyan-500/30 bg-cyan-500/10 shadow-[0_0_15px_rgba(34,211,238,0.1)] group-hover:border-cyan-400 group-hover:shadow-[0_0_20px_rgba(34,211,238,0.2)] transition-all">
                  <img
                    src="/logo.png"
                    alt="Anamnesis-AI logo"
                    className="h-full w-full object-contain p-0.5"
                  />
                </div>
                <span className="bg-gradient-to-r from-slate-100 to-slate-300 bg-clip-text text-sm font-bold tracking-tight text-transparent group-hover:to-cyan-200">
                  Anamnesis-AI
                </span>
              </Link>
            </div>

            {/* Navigation Links */}
            <nav className="hidden xl:flex items-center gap-1">
              {links.map((link) => {
                const isActive = pathname === link.href;
                const Icon = link.icon;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`relative flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-medium tracking-wide transition-all duration-200 ${
                      isActive
                        ? "text-cyan-400"
                        : "text-slate-400 hover:text-slate-100"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{link.label}</span>
                    {isActive && (
                      <span className="absolute bottom-0 left-2.5 right-2.5 h-0.5 bg-cyan-400 rounded-full" />
                    )}
                  </Link>
                );
              })}
            </nav>

            {/* Search Trigger & Launch CTA */}
            <div className="flex items-center gap-3">
              {/* CMD+K Search Trigger */}
              <button
                type="button"
                onClick={() => setIsPaletteOpen(true)}
                className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 py-1.5 text-[10px] text-slate-400 hover:text-slate-200 hover:bg-white/10 transition"
              >
                <Search className="h-3.5 w-3.5 text-slate-500" />
                <span className="hidden sm:inline font-mono">CMD+K</span>
              </button>

              <Link
                href="/simulation"
                className="inline-flex h-9 items-center justify-center rounded-lg bg-gradient-to-r from-cyan-500 to-violet-600 px-4 text-xs font-bold text-slate-950 transition hover:brightness-110 active:scale-[0.98] shadow-lg shadow-cyan-500/10"
              >
                Launch Lab
              </Link>
              <SoundToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Render Command Palette Modal */}
      <CommandPalette isOpen={isPaletteOpen} onClose={() => setIsPaletteOpen(false)} />
    </>
  );
}
