"use client";

import { BookOpen, Search, ArrowRight, ShieldCheck, FileSpreadsheet, BrainCircuit } from "lucide-react";

export default function MethodologyPage() {
  return (
    <main className="min-h-screen bg-black px-6 py-12 relative overflow-hidden select-none">
      <div className="absolute top-1/4 right-1/4 w-[400px] h-[400px] ambient-glow" />

      <div className="mx-auto max-w-4xl space-y-12 relative z-10">
        {/* Header */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 text-mono-label text-cyan-400">
            <BookOpen className="h-3.5 w-3.5" />
            <span>Research / Methodology</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Simulation Methodology
          </h1>
          <p className="text-sm font-light text-slate-400">
            Scientific guidelines, retrieval algorithms, and checking matrices governing the alternate timeline generation.
          </p>
        </div>

        {/* Section 1: Retrieval Augmented Generation */}
        <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-500/20 bg-cyan-500/5 text-cyan-400">
              <Search className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-bold text-white">1. Knowledge Retrieval Layer (RAG)</h2>
          </div>
          <p className="text-xs text-slate-300 font-light leading-7">
            Every simulation begins with dynamic context loading. Before any agent generates a
            single word, the retrieval system runs asynchronous queries across six free sources:
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-lg border border-white/5 bg-slate-950/40 p-5 space-y-2">
              <h4 className="text-xs font-bold text-slate-200">Wikipedia</h4>
              <p className="text-[11px] text-slate-400 leading-5 font-light">
                Historical events, figures, and baseline policy records around the divergence point.
              </p>
            </div>
            <div className="rounded-lg border border-white/5 bg-slate-950/40 p-5 space-y-2">
              <h4 className="text-xs font-bold text-slate-200">arXiv</h4>
              <p className="text-[11px] text-slate-400 leading-5 font-light">
                Research abstracts on economic models, climate science, and computing architectures.
              </p>
            </div>
            <div className="rounded-lg border border-white/5 bg-slate-950/40 p-5 space-y-2">
              <h4 className="text-xs font-bold text-slate-200">World Bank</h4>
              <p className="text-[11px] text-slate-400 leading-5 font-light">
                GDP, population, electricity access, and CO₂ indicators to anchor economic claims.
              </p>
            </div>
            <div className="rounded-lg border border-white/5 bg-slate-950/40 p-5 space-y-2">
              <h4 className="text-xs font-bold text-slate-200">UN Data</h4>
              <p className="text-[11px] text-slate-400 leading-5 font-light">
                Sustainable development and social indicators — SDG goals, literacy, life expectancy.
              </p>
            </div>
            <div className="rounded-lg border border-white/5 bg-slate-950/40 p-5 space-y-2">
              <h4 className="text-xs font-bold text-slate-200">NASA</h4>
              <p className="text-[11px] text-slate-400 leading-5 font-light">
                Earth science and planetary data for long-horizon climate and technology context.
              </p>
            </div>
            <div className="rounded-lg border border-white/5 bg-slate-950/40 p-5 space-y-2">
              <h4 className="text-xs font-bold text-slate-200">NOAA</h4>
              <p className="text-[11px] text-slate-400 leading-5 font-light">
                Temperature, precipitation, and carbon records that ground environmental outcomes.
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-300 font-light leading-7">
            Retrieved documents are chunked, embedded into ChromaDB, and re-ranked before the top
            passages — with their source citations — are injected into every agent prompt.
          </p>
        </section>

        {/* Section 2: Parallel Multi-Agent Mappings */}
        <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-violet-500/20 bg-violet-500/5 text-violet-400">
              <BrainCircuit className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-bold text-white">2. Parallel Domain Collaboration</h2>
          </div>
          <p className="text-xs text-slate-300 font-light leading-7">
            Agents process in a fan-out / fan-in graph. The Historian first reconstructs baseline reality and the divergence point. Eight domain agents — economy, technology, society, climate, politics, energy, healthcare and demographics — then evaluate the consequences in parallel, each contributing analysis text, timeline events and a −100 to +100 impact score.
          </p>
          
          {/* Horizontal workflow representation */}
          <div className="rounded-xl border border-white/5 bg-slate-950/60 p-5 space-y-3">
            <span className="text-[9px] font-bold uppercase tracking-wider text-cyan-400">Agent Flow Sequence</span>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
              <div className="font-semibold text-slate-200">Historian Baseline</div>
              <ArrowRight className="hidden sm:block h-3.5 w-3.5 text-slate-700" />
              <div className="font-semibold text-slate-200">8 Parallel Domain Agents</div>
              <ArrowRight className="hidden sm:block h-3.5 w-3.5 text-slate-700" />
              <div className="font-semibold text-slate-200">Critic Audit (+ feedback loop)</div>
              <ArrowRight className="hidden sm:block h-3.5 w-3.5 text-slate-700" />
              <div className="font-semibold text-slate-200">Narrator Synthesis</div>
            </div>
          </div>
        </section>

        {/* Section 3: Critic Scoring */}
        <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-amber-500/20 bg-amber-500/5 text-amber-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-bold text-white">3. Critic Validation & Plausibility Scoring</h2>
          </div>
          <p className="text-xs text-slate-300 font-light leading-7">
            The Critic Agent audits all nine agent outputs together. It looks for cross-agent contradictions (for example, one agent implying rapid technological progress while another describes an unexplained economic collapse) and for unrealistic or extreme claims. From that audit it reports:
          </p>
          <div className="rounded-xl border border-white/5 bg-slate-950/60 p-5 space-y-3 text-xs font-mono leading-6 text-slate-400">
            <div>• confidence_score — one 0–100 rating for the whole simulation, with a written justification.</div>
            <div>• agent_confidences — a separate 0–100 rating and explanation for each agent.</div>
            <div>• risk_notes — 1–4 specific inconsistencies, unsupported claims or caveats.</div>
          </div>
          <p className="text-xs text-slate-300 font-light leading-7">
            If the overall confidence falls below the threshold (75), the Critic's notes are fed back and the pipeline re-runs — up to 2 iterations — before the Narrator compiles the report. After that, three deterministic checks complete the score: <strong className="text-slate-200">grounding</strong> (how well each analysis is supported by the retrieved sources), <strong className="text-slate-200">uncertainty</strong> (variance between the agents' impact scores) and <strong className="text-slate-200">calibration</strong> (chronological sanity of the unified timeline).
          </p>
        </section>
      </div>
    </main>
  );
}
