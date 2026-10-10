"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Terminal, X, Play, Shield } from "lucide-react";
import { createScenario } from "../lib/api";

export default function FloatingLauncher() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleLaunch = async () => {
    const trimmed = query.trim();
    if (!trimmed || isSubmitting) return;

    setIsSubmitting(true);
    setError("");

    try {
      const result = await createScenario(trimmed);
      setIsOpen(false);
      setQuery("");
      router.push(`/simulation/${result.scenario_id}`);
    } catch (err) {
      setError("Failed to trigger simulation.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="no-print fixed bottom-6 right-6 z-[80] font-sans">
      {/* Popover Card */}
      {isOpen && (
        <div className="mb-3 w-80 rounded-xl border border-white/10 bg-slate-950/95 p-4 shadow-2xl glass-panel animate-fade-in-up">
          <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
            <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-cyan-400 font-mono">
              <Shield className="h-3.5 w-3.5" /> Quick Sandbox Launcher
            </div>
            <button 
              type="button" 
              onClick={() => setIsOpen(false)}
              className="text-slate-500 hover:text-white transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type quick alternate history scenario..."
            className="w-full min-h-20 rounded-lg border border-white/5 bg-slate-950/50 p-2.5 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-500/25 resize-none font-light leading-5"
          />

          {error && <p className="text-[10px] text-rose-400 my-1 animate-pulse">{error}</p>}

          <button
            type="button"
            onClick={handleLaunch}
            disabled={!query.trim() || isSubmitting}
            className="w-full mt-2 inline-flex h-8 items-center justify-center gap-1.5 rounded-lg bg-cyan-400 text-[10px] font-bold uppercase tracking-wider text-slate-950 transition hover:brightness-110 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <span className="h-3 w-3 animate-spin rounded-full border border-slate-950/30 border-t-slate-950" />
                <span>Launching...</span>
              </>
            ) : (
              <>
                <Play className="h-3 w-3 fill-slate-950" />
                <span>Run Simulation</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex h-12 w-12 items-center justify-center rounded-full border border-cyan-500/30 bg-slate-950 text-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.15)] hover:border-cyan-400 hover:shadow-[0_0_25px_rgba(34,211,238,0.25)] hover:scale-105 active:scale-[0.95] transition-all"
      >
        {isOpen ? <X className="h-5 w-5 animate-pulse" /> : <Terminal className="h-5 w-5" />}
      </button>
    </div>
  );
}
