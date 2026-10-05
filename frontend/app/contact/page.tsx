"use client";

import { Users, Globe, ExternalLink, Code, Palette, Server, Database, Brain } from "lucide-react";

const TEAM = [
  {
    name: "Pratik Singh",
    role: "Frontend Development & Coordination",
    bio: "Built the Next.js frontend — pages, components, state flow and the simulation/report experience — and kept the workflow moving through planning, review and integration across the project.",
    icon: Code,
    color: "text-cyan-400 border-cyan-500/20 bg-cyan-500/5 group-hover:border-cyan-400/40"
  },
  {
    name: "Yashika Singh",
    role: "UI/UX & Interface Design",
    bio: "Shaped the experience end to end: layout systems, theme and visual language, typography hierarchy, responsive behaviour and the interaction polish on every screen.",
    icon: Palette,
    color: "text-pink-400 border-pink-500/20 bg-pink-500/5 group-hover:border-pink-400/40"
  },
  {
    name: "Prabhat Vishwakarma",
    role: "API Endpoints & Data Sources",
    bio: "Designed the REST endpoints the platform runs on and the data-source layer behind the agents, wiring Wikipedia, arXiv, World Bank, UN Data, NASA and NOAA into retrieval for grounded reasoning.",
    icon: Server,
    color: "text-amber-400 border-amber-500/20 bg-amber-500/5 group-hover:border-amber-400/40"
  },
  {
    name: "Ananya Singh",
    role: "Database Systems",
    bio: "Handled all database-related work: schema design, persistence of scenarios and reports, query paths, migrations and the data layer every simulation run reads and writes.",
    icon: Database,
    color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5 group-hover:border-emerald-400/40"
  },
  {
    name: "Aryama Srivastava",
    role: "Agentic AI & Intelligence Layer",
    bio: "Worked on the research and core functionality of the agentic AI layer — the orchestrator, agent coordination and reasoning intelligence that drive multi-agent decision-making.",
    icon: Brain,
    color: "text-violet-400 border-violet-500/20 bg-violet-500/5 group-hover:border-violet-400/40"
  }
];

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-black px-6 py-12 relative overflow-hidden select-none">
      <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] ambient-glow" />

      <div className="mx-auto max-w-5xl space-y-12 relative z-10">
        {/* Header */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 text-mono-label text-cyan-400">
            <Users className="h-3.5 w-3.5" />
            <span>Organization / Team</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Meet the Team Behind Anamnesis-AI
          </h1>
          <p className="text-sm font-light text-slate-400 leading-relaxed max-w-3xl">
            A multidisciplinary team spanning frontend engineering, UI/UX design, APIs and data
            sources, database systems, and agentic AI research — together building an intelligent
            alternate-reality simulation platform.
          </p>
        </div>

        {/* Team Grid */}
        <div className="flex flex-wrap justify-center gap-6">
          {TEAM.map((member, index) => {
            const Icon = member.icon;
            return (
              <div
                key={index}
                className="w-full sm:w-[calc(50%-12px)] lg:w-[calc(33.333%-16px)] rounded-2xl border border-white/5 bg-slate-950/35 p-6 transition-all duration-300 hover:border-white/10 hover:bg-slate-950/65 hover:-translate-y-1 hover:shadow-[0_10px_30px_rgba(34,211,238,0.05)] flex flex-col group justify-between"
              >
                <div>
                  <div className="flex items-center gap-3.5 mb-4">
                    <div className={`flex h-11 w-11 items-center justify-center rounded-xl border ${member.color} transition-all duration-300 group-hover:scale-105`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-200 group-hover:text-white transition-colors duration-300">
                        {member.name}
                      </h3>
                      <span className="text-[9px] font-bold uppercase tracking-wider text-cyan-400 font-mono block mt-0.5">
                        {member.role}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed font-light">
                    {member.bio}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Source & Contributions Card */}
        <div className="rounded-2xl glass-panel p-8 shadow-2xl relative overflow-hidden">
          <h2 className="text-lg font-bold text-white mb-2">Source Code & Contributions</h2>
          <p className="text-xs text-slate-400 leading-6 font-light mb-6">
            Anamnesis-AI is open source. Browse the codebase, report a bug, or suggest a feature —
            everything lives in the public repository.
          </p>

          <div className="grid gap-4 sm:grid-cols-2">
            <a href="https://github.com/Anamnesis-AI-Org/Anamnesis-AI" target="_blank" rel="noreferrer" className="flex items-center gap-3 rounded-lg border border-white/5 bg-slate-950/45 p-4 hover:border-cyan-500/25 transition-colors">
              <Globe className="h-5 w-5 text-cyan-400" />
              <div>
                <h4 className="text-xs font-bold text-slate-200">GitHub Repository</h4>
                <span className="text-[9px] text-slate-500 font-mono">Anamnesis-AI-Org/Anamnesis-AI</span>
              </div>
            </a>

            <a href="https://github.com/Anamnesis-AI-Org/Anamnesis-AI/issues" target="_blank" rel="noreferrer" className="flex items-center gap-3 rounded-lg border border-white/5 bg-slate-950/45 p-4 hover:border-cyan-500/25 transition-colors">
              <ExternalLink className="h-5 w-5 text-violet-400" />
              <div>
                <h4 className="text-xs font-bold text-slate-200">Issues & Requests</h4>
                <span className="text-[9px] text-slate-500 font-mono">Report bugs and propose ideas</span>
              </div>
            </a>
          </div>
        </div>
      </div>
    </main>
  );
}
