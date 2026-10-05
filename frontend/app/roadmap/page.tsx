"use client";

import { Milestone, Compass, Milestone as MilestoneIcon, CheckCircle2, Circle } from "lucide-react";

const PHASES = [
  {
    phase: "Phase 1",
    status: "Completed",
    title: "Grounded Multi-Agent Pipeline",
    desc: "Nine domain agents plus a Critic running on a LangGraph fan-out/fan-in graph, grounded by RAG across six free sources (Wikipedia, arXiv, World Bank, UN Data, NASA, NOAA) stored in ChromaDB."
  },
  {
    phase: "Phase 2",
    status: "Completed",
    title: "Trust & Explainability Layer",
    desc: "Causal graph extraction, assumption registry, per-agent grounding validation, and the confidence, uncertainty and calibration scores attached to every report."
  },
  {
    phase: "Phase 3",
    status: "Completed",
    title: "Exploration Lab & Branching",
    desc: "Interactive Q&A over reports, structured agent debates, parameter re-simulation with sliders, timeline branching from any event, and side-by-side report comparison."
  },
  {
    phase: "Phase 4",
    status: "Completed",
    title: "Production Deployment",
    desc: "Hosted on Vercel (frontend) with Render and Supabase (backend), full CI, and a 105-test suite covering the API, agents, RAG, simulation and validation layers."
  },
  {
    phase: "Phase 5",
    status: "Planned",
    title: "Rate-Limit Hardening & Grounding Depth",
    desc: "Honor Gemini retry delays with a request scheduler for the free-tier 15 req/min cap, and pass full source text (not just citations) into the grounding validator."
  }
];

export default function RoadmapPage() {
  return (
    <main className="min-h-screen bg-black px-6 py-12 relative overflow-hidden select-none">
      <div className="absolute top-1/4 left-1/3 w-[500px] h-[500px] ambient-glow" />

      <div className="mx-auto max-w-4xl space-y-12 relative z-10">
        {/* Header */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 text-mono-label text-cyan-400">
            <MilestoneIcon className="h-3.5 w-3.5" />
            <span>Development / Roadmap</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Development Roadmap
          </h1>
          <p className="text-sm font-light text-slate-400">
            What has been built so far, and what comes next for the Anamnesis-AI research platform.
          </p>
        </div>

        {/* Timeline phases */}
        <div className="space-y-6 relative pl-6">
          <div className="absolute left-3.5 top-2 bottom-2 w-px bg-gradient-to-b from-cyan-400 via-violet-500 to-transparent" />

          {PHASES.map((ph, index) => {
            const isCompleted = ph.status === "Completed";
            return (
              <div key={index} className="relative flex gap-6 animate-slide-in">
                <div className="absolute left-[-1.15rem] top-1.5 z-10 flex items-center justify-center">
                  {isCompleted ? (
                    <CheckCircle2 className="h-5.5 w-5.5 text-cyan-400 bg-black rounded-full" />
                  ) : (
                    <Circle className="h-5.5 w-5.5 text-slate-700 bg-black rounded-full" />
                  )}
                </div>
                
                <div className="flex-grow rounded-xl border border-white/5 bg-slate-950/35 p-6 shadow-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 font-mono">{ph.phase}</span>
                    <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
                      isCompleted 
                        ? "bg-cyan-500/10 border-cyan-500/20 text-cyan-400" 
                        : "bg-slate-900 border-slate-800 text-slate-500"
                    }`}>
                      {ph.status}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-200">{ph.title}</h3>
                  <p className="text-xs text-slate-400 leading-6 font-light">{ph.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </main>
  );
}
