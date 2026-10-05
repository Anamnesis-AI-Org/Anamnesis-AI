"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { History, Globe, TrendingUp, Cpu, Users, Landmark, Orbit, ArrowRight, Play, Terminal, GitBranch, ArrowLeft } from "lucide-react";
import { createScenario, branchScenario, getScenarioReport } from "../../lib/api";
import type { UnifiedTimelineEvent } from "../../lib/types";

const CATEGORIES = [
  { key: "all", label: "All Categories", icon: Terminal },
  { key: "history", label: "History", icon: History },
  { key: "climate", label: "Climate", icon: Globe },
  { key: "economics", label: "Economics", icon: TrendingUp },
  { key: "technology", label: "Technology", icon: Cpu },
  { key: "society", label: "Society", icon: Users },
  { key: "politics", label: "Politics", icon: Landmark },
  { key: "space", label: "Space Exploration", icon: Orbit }
];

const TEMPLATES = [
  { category: "history", text: "What if the Roman Empire never fell?", label: "Roman Empire Preservation" },
  { category: "history", text: "What if the Library of Alexandria was never destroyed?", label: "Alexandrian Science" },
  { category: "climate", text: "What if the Sahara became a forest?", label: "Saharan Hydration" },
  { category: "climate", text: "What if carbon capture was fully industrialized in 1950?", label: "1950s Sequestration" },
  { category: "economics", text: "What if AI replaced 50% of office jobs?", label: "Labor Automation Restructure" },
  { category: "economics", text: "What if gold was never discovered?", label: "Analog Paper-Ledger Trade" },
  { category: "technology", text: "What if computing remained analog?", label: "Vacuum & Gear Computation" },
  { category: "technology", text: "What if EVs became mainstream in 1990?", label: "California ZEV Mandate" },
  { category: "society", text: "What if the internet never existed?", label: "Local Media Cooperatives" },
  { category: "politics", text: "What if the United Nations had direct global legislative authority?", label: "UN Sovereignty" },
  { category: "space", text: "What if the space race reached Mars by 1980?", label: "Early Mars Colonization" }
];

function SimulationConfigContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const parentId = searchParams?.get("parent_id") || "";
  const eventId = searchParams?.get("event_id") || "";

  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [parentEvent, setParentEvent] = useState<UnifiedTimelineEvent | null>(null);
  const [isLoadingParent, setIsLoadingParent] = useState(false);

  useEffect(() => {
    if (!parentId || !eventId) {
      setParentEvent(null);
      return;
    }

    let active = true;
    const loadParentDetails = async () => {
      setIsLoadingParent(true);
      try {
        const report = await getScenarioReport(parentId);
        if (!active) return;
        const matched = report.alternate_timeline.find(
          (ev, idx) => (ev.id || `${ev.year}-${idx}`) === eventId || ev.id === eventId
        );
        if (matched) {
          setParentEvent(matched);
        }
      } catch (err) {
        console.error("Failed to load parent scenario details for branching:", err);
      } finally {
        if (active) setIsLoadingParent(false);
      }
    };

    void loadParentDetails();
    return () => {
      active = false;
    };
  }, [parentId, eventId]);

  const filteredTemplates = TEMPLATES.filter(
    (t) => activeCategory === "all" || t.category === activeCategory
  );

  const handleLaunch = async (textToRun = query) => {
    const trimmed = textToRun.trim();
    if (!trimmed || isSubmitting) return;

    setIsSubmitting(true);
    setError("");

    try {
      let result;
      if (parentId && eventId) {
        result = await branchScenario(parentId, eventId, trimmed);
      } else {
        result = await createScenario(trimmed);
      }
      router.push(`/simulation/${result.scenario_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger simulation. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-black px-6 py-12 relative overflow-hidden select-none">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/3 w-[500px] h-[500px] ambient-glow" />

      <div className="mx-auto max-w-4xl space-y-10 relative z-10">
        {/* Header */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 text-mono-label text-cyan-400">
            <Terminal className="h-3.5 w-3.5" />
            <span>Workspace / Simulation Lab</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Configure Alternate Timeline
          </h1>
          <p className="text-sm font-light text-slate-400">
            Compose a custom divergence query or seed from our structured research templates below.
          </p>
        </div>

        {/* Branching Banner Context */}
        {parentId && eventId && (
          <div className="rounded-2xl border border-violet-500/20 bg-violet-955/15 p-5 space-y-3 relative overflow-hidden shadow-2xl">
            <div className="absolute top-0 right-0 p-8 opacity-[0.03] pointer-events-none">
              <GitBranch className="h-24 w-24 text-violet-400" />
            </div>
            
            <div className="flex items-center justify-between gap-3">
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-violet-400 flex items-center gap-1.5 animate-pulse">
                <GitBranch className="h-3.5 w-3.5 animate-bounce" /> Branching Scenario timeline fork
              </span>
              <button
                type="button"
                onClick={() => {
                  router.push("/simulation");
                  setParentEvent(null);
                }}
                className="text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1"
              >
                <ArrowLeft className="h-3 w-3" /> Cancel Branch
              </button>
            </div>
            
            {isLoadingParent ? (
              <p className="text-xs text-slate-500 font-mono animate-pulse">
                Retrieving parent timeline context...
              </p>
            ) : parentEvent ? (
              <div className="space-y-1.5">
                <p className="text-xs font-semibold text-white leading-normal">
                  Diverging at CE {parentEvent.year} from:
                </p>
                <p className="text-xs text-violet-300/90 leading-relaxed font-light border-l border-violet-500/30 pl-3 italic">
                  "{parentEvent.event}"
                </p>
              </div>
            ) : (
              <p className="text-xs text-slate-500 font-mono">
                Parent event details loaded. Branching from CE timeline context.
              </p>
            )}
          </div>
        )}

        {/* Input Card */}
        <div className="rounded-2xl glass-panel p-6 sm:p-8 shadow-2xl relative">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <label htmlFor="scenario-prompter" className="text-mono-label text-slate-400">
                {parentId && eventId ? "Branch Alternative Event Description" : "Modification Prompt"}
              </label>
              {query.length > 0 && (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  className="text-[10px] font-bold uppercase tracking-wider text-slate-600 hover:text-slate-300 transition-colors"
                >
                  Clear Prompt
                </button>
              )}
            </div>

            <textarea
              id="scenario-prompter"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={parentId && eventId ? "E.g., What if they failed to contain the event, leading to a localized technological containment breach?" : "E.g., What if computing remained analog and mechanical slide-rules reached sub-nanometer gear precision?"}
              className="min-h-36 w-full rounded-xl border border-white/5 bg-slate-950/65 px-4 py-4 text-sm text-slate-100 placeholder:text-slate-600 focus:border-cyan-500/25 focus:ring-4 focus:ring-cyan-500/5 outline-none transition duration-300 resize-none font-light"
            />

            <div className="flex items-center justify-between gap-4 pt-2 border-t border-white/5">
              <span className="text-[11px] font-light text-slate-500">
                {parentId && eventId ? "Branch locks in pre-divergence events." : "Graph runs 9 domain agents & critic checks."}
              </span>
              <button
                type="button"
                onClick={() => handleLaunch()}
                disabled={!query.trim() || isSubmitting}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 px-6 py-3 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:brightness-110 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
              >
                {isSubmitting ? (
                  <>
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-950/30 border-t-slate-950" />
                    <span>Launching...</span>
                  </>
                ) : (
                  <>
                    {parentId && eventId ? (
                      <>
                        <GitBranch className="h-3.5 w-3.5 text-slate-950" />
                        <span>Diverge Timeline & Run</span>
                      </>
                    ) : (
                      <>
                        <Play className="h-3.5 w-3.5 fill-slate-950" />
                        <span>Run Simulation</span>
                      </>
                    )}
                  </>
                )}
              </button>
            </div>

            {error && <p className="text-xs font-semibold text-rose-400 mt-2 animate-pulse">{error}</p>}
          </div>
        </div>

        {/* Templates Selector */}
        <div className="space-y-6">
          <div className="flex flex-wrap gap-1.5 border-b border-white/5 pb-4">
            {CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              const isSelected = activeCategory === cat.key;
              return (
                <button
                  key={cat.key}
                  type="button"
                  onClick={() => setActiveCategory(cat.key)}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                    isSelected
                      ? "bg-white/5 text-cyan-400 border border-cyan-500/15"
                      : "text-slate-400 hover:text-slate-200 border border-transparent"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {cat.label}
                </button>
              );
            })}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredTemplates.map((tpl) => (
              <button
                key={tpl.text}
                type="button"
                onClick={() => {
                  setQuery(tpl.text);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="group rounded-xl border border-white/5 bg-slate-950/35 p-5 text-left transition hover:scale-[1.01] hover:border-cyan-500/25 hover:bg-cyan-500/5 hover-glow"
              >
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 group-hover:text-cyan-400/80 transition-colors">
                  {tpl.category.toUpperCase()} Template
                </span>
                <h3 className="my-2 text-xs font-semibold text-slate-300 leading-5 group-hover:text-white transition-colors">
                  {tpl.label}
                </h3>
                <p className="text-xs text-slate-500 line-clamp-2 leading-5 font-light group-hover:text-slate-400 transition-colors">
                  {tpl.text}
                </p>
                <div className="flex items-center gap-1 mt-4 text-[10px] uppercase font-bold tracking-wider text-slate-600 group-hover:text-cyan-400 transition-colors opacity-0 group-hover:opacity-100">
                  Select <ArrowRight className="h-3 w-3" />
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}

export default function SimulationConfigPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-black flex items-center justify-center">
        <span className="text-cyan-400 font-mono animate-pulse">Initializing Lab...</span>
      </div>
    }>
      <SimulationConfigContent />
    </Suspense>
  );
}
