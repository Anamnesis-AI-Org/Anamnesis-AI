"use client";

import { useState } from "react";
import { Terminal, Activity, ArrowRight, Layers, Cpu, ShieldAlert, FileText, Search } from "lucide-react";

const NODES = [
  {
    id: "user",
    label: "User Prompt",
    icon: Terminal,
    desc: "The initial alternate history query submitted by the user configuring the pivot year.",
    details: "Inputs: Raw text string (e.g. 'What if Alexandria's Library was saved?')"
  },
  {
    id: "orchestrator",
    label: "Orchestrator Node",
    icon: Activity,
    desc: "Calculates focus domains, divergence year bounds, and routes retrieval tasks.",
    details: "Outputs: JSON structure containing divergence_year, focus_domains, and time_horizon."
  },
  {
    id: "rag",
    label: "Knowledge Retrieval (RAG)",
    icon: Search,
    desc: "Queries six free sources — Wikipedia, arXiv, World Bank, UN Data, NASA and NOAA — then chunks, embeds and re-ranks passages in ChromaDB.",
    details: "Yields: a citation-rich reference block injected into every agent prompt."
  },
  {
    id: "historian",
    label: "Historian Agent",
    icon: Layers,
    desc: "Traces primary divergence milestones and geopolitical border changes.",
    details: "Outputs: timeline_events list (year, event) & baseline analysis."
  },
  {
    id: "domains",
    label: "Domain Cluster (8 Agents)",
    icon: Cpu,
    desc: "Economy, technology, society, climate, politics, energy, healthcare and demographics analyse the divergence in parallel, seeded by the Historian baseline.",
    details: "Outputs: individual analysis texts, timeline events, and impact scores (-100 to +100)."
  },
  {
    id: "critic",
    label: "Critic Agent",
    icon: ShieldAlert,
    desc: "Audits timeline consistency, flags contradictions and extreme claims, and scores overall plausibility.",
    details: "Outputs: confidence_score (0-100), per-agent confidences, risk notes. Below 75 it feeds notes back and the pipeline re-runs (max 2 iterations)."
  },
  {
    id: "narrator",
    label: "Narrator Node",
    icon: FileText,
    desc: "Synthesizes final timeline, resolves domain disputes, and outputs report models.",
    details: "Result: Complete JSON FinalReport object sent to database."
  }
];

export default function ArchitecturePage() {
  const [activeNode, setActiveNode] = useState("user");
  const selected = NODES.find((n) => n.id === activeNode) || NODES[0];

  return (
    <main className="min-h-screen bg-black px-6 py-12 relative overflow-hidden select-none">
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] ambient-glow" />

      <div className="mx-auto max-w-5xl space-y-10 relative z-10">
        {/* Header */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 text-mono-label text-cyan-400">
            <Layers className="h-3.5 w-3.5" />
            <span>Architecture / System Mappings</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Agent Pipelines
          </h1>
          <p className="text-sm font-light text-slate-400">
            Click on pipeline nodes in the graph to inspect token exchange shapes, parameters, and details.
          </p>
        </div>

        {/* Layout Grid */}
        <div className="grid gap-8 lg:grid-cols-12">
          {/* Left: Interactive Diagram Map */}
          <div className="lg:col-span-7 rounded-2xl border border-white/5 bg-[#070708] p-6 shadow-2xl flex flex-col justify-center gap-4 relative min-h-[400px]">
            <div className="absolute top-4 left-4 text-[9px] uppercase font-bold tracking-widest text-slate-600 font-mono">
              Interactive Network Graph
            </div>

            <div className="space-y-4 pt-8">
              {NODES.map((node, index) => {
                const isSelected = activeNode === node.id;
                const Icon = node.icon;
                return (
                  <div key={node.id} className="flex flex-col items-center">
                    <button
                      type="button"
                      onClick={() => setActiveNode(node.id)}
                      className={`flex w-64 items-center gap-3.5 rounded-xl border px-4 py-3 text-left transition-all ${
                        isSelected
                          ? "border-cyan-400 bg-cyan-500/10 text-cyan-200 shadow-[0_0_15px_rgba(34,211,238,0.1)]"
                          : "border-white/5 bg-slate-950/45 text-slate-400 hover:border-white/10 hover:text-slate-200"
                      }`}
                    >
                      <Icon className={`h-4.5 w-4.5 ${isSelected ? "text-cyan-400" : "text-slate-500"}`} />
                      <span className="text-xs font-semibold">{node.label}</span>
                    </button>
                    {index < NODES.length - 1 && (
                      <div className="my-2 h-6 w-px bg-gradient-to-b from-cyan-400/80 to-transparent" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: Selected Node Details Inspector */}
          <div className="lg:col-span-5 rounded-2xl glass-panel p-6 sm:p-8 shadow-2xl flex flex-col justify-between">
            <div className="space-y-6">
              <div className="flex items-center gap-3 pb-3 border-b border-white/5">
                <selected.icon className="h-5 w-5 text-cyan-400" />
                <h3 className="text-md font-bold text-white">{selected.label}</h3>
              </div>

              <div className="space-y-4">
                <div className="space-y-1">
                  <span className="text-[9px] uppercase font-bold tracking-widest text-slate-500">Node Description</span>
                  <p className="text-xs leading-6 text-slate-300 font-light">{selected.desc}</p>
                </div>

                <div className="rounded-lg border border-white/5 bg-slate-950/65 p-4 font-mono text-[10px] leading-5 text-slate-400">
                  {selected.details}
                </div>
              </div>
            </div>

            <div className="pt-6 border-t border-white/5 text-[9px] text-slate-500 leading-4 font-light">
              This graph maps the exact LangGraph execution sequence implemented in `backend/app/orchestrator.py`.
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
