"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { 
  BookOpen, Globe, TrendingUp, Cpu, Users, ShieldCheck, FileText, 
  ArrowRight, CheckCircle2, Play, Terminal, HelpCircle, Shield, 
  ChevronLeft, ChevronRight, Activity, Sparkles 
} from "lucide-react";

import CanvasParticles from "../components/CanvasParticles";
import HeroNebula from "../components/HeroNebula";
import InfiniteTimeline from "../components/InfiniteTimeline";
import { MOCK_SCENARIOS } from "../lib/mockScenarios";
import { createScenario } from "../lib/api";
import { gsap } from "gsap";
import { useReducedMotion } from "../utils/useReducedMotion";

const AGENT_SHOWCASE = [
  {
    key: "historian",
    label: "Historian Agent",
    icon: BookOpen,
    color: "text-cyan-400 border-cyan-500/20 bg-cyan-500/5",
    focus: "Divergence Branching & Timelines",
    description: "Determines the precise pivot points in historical timelines, tracing how geopolitical events cascade and branch out after key modifications.",
    insight: "Preserving the Library of Alexandria extends early Roman science, moving industrialization forward by 800 years."
  },
  {
    key: "climate",
    label: "Climate Agent",
    icon: Globe,
    color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5",
    focus: "Ecological Feedbacks",
    description: "Models carbon cycle adjustments, precipitation patterns, local temperature variance, and biodiversity modifications caused by alternate resource use.",
    insight: "Widespread electric logistics in 1990 lowers atmospheric carbon concentration by 45 ppm, avoiding extreme warming cycles."
  },
  {
    key: "economist",
    label: "Economist Agent",
    icon: TrendingUp,
    color: "text-amber-400 border-amber-500/20 bg-amber-500/5",
    focus: "Macro-Finance & Labor",
    description: "Computes changes in trade corridors, wealth distributions, tax structure adjustments, and labor transitions resulting from technological changes.",
    insight: "Taxing automated computing capacity instead of corporate profits creates stable funding for localized universal basic dividends."
  },
  {
    key: "technology",
    label: "Technology Agent",
    icon: Cpu,
    color: "text-violet-400 border-violet-500/20 bg-violet-500/5",
    focus: "Systemic Innovation Vectors",
    description: "Simulates parallel tech structures—such as analog slide-rules, vacuum tubes, or solid-state grids—projecting custom resource demands.",
    insight: "Analog computing avoids the modern digital software vulnerabilities but limits the speed of decentralized communications."
  },
  {
    key: "society",
    label: "Society Agent",
    icon: Users,
    color: "text-pink-400 border-pink-500/20 bg-pink-500/5",
    focus: "Cultural Mappings & Shifts",
    description: "Explores demographic shifts, vocational alterations, community media structures, and identity pivots in the face of macro change.",
    insight: "The absence of digital databases limits global migration speed but strengthens community civic cooperatives."
  },
  {
    key: "critic",
    label: "Critic Agent",
    icon: ShieldCheck,
    color: "text-rose-400 border-rose-500/20 bg-rose-500/5",
    focus: "Simulation Coherency",
    description: "Audits agent responses for logical contradictions, unsupported projections, or speed anomalies, calculating a total confidence score.",
    insight: "Identifies timeline conflicts where industrial progress assumes mineral availability before trade routes open."
  },
  {
    key: "narrator",
    label: "Narrator Node",
    icon: FileText,
    color: "text-indigo-400 border-indigo-500/20 bg-indigo-500/5",
    focus: "Executive Synthesis",
    description: "Aggregates the multi-agent timelines, resolves conflicts, and outputs the final executive report and indicators.",
    insight: "Synthesizes economic, social, and climate indicators into a clean, uniform parallel historical record."
  }
];

const HOW_IT_WORKS = [
  { step: "01", name: "User Scenario", desc: "Submit an alternate history query or timeline modification request." },
  { step: "02", name: "Retrieval (RAG)", desc: "Relevant context is loaded in parallel from six free sources — encyclopedias, research papers and public data portals." },
  { step: "03", name: "Agent Collab", desc: "The Historian sets the baseline, then eight domain agents analyse the divergence in parallel, calculating secondary cross-domain impacts." },
  { step: "04", name: "Critic Validation", desc: "Critic audits timeline consistency and flags logical contradictions." },
  { step: "05", name: "Executive Report", desc: "A unified alternate timeline, risk log, and gauges dashboard are compiled." }
];

export default function LandingPage() {
  const router = useRouter();
  const [quickQuery, setQuickQuery] = useState("");
  const [isLaunching, setIsLaunching] = useState(false);
  const [activeTab, setActiveTab] = useState("historian");
  const [carouselIndex, setCarouselIndex] = useState(0);
  
  const heroRef = useRef<HTMLDivElement>(null);

  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (reducedMotion) {
      if (heroRef.current) gsap.set(heroRef.current, { opacity: 1 });
      return;
    }
    const el = heroRef.current;
    if (el) {
      gsap.fromTo(
        el,
        { opacity: 0, y: -30 },
        { opacity: 1, y: 0, duration: 1, ease: "power2.out" }
      );
    }
  }, [reducedMotion]);

  const activeAgent = AGENT_SHOWCASE.find((a) => a.key === activeTab) || AGENT_SHOWCASE[0];
  const ActiveIcon = activeAgent.icon;

  const handleQuickLaunch = async () => {
    const trimmed = quickQuery.trim();
    if (!trimmed || isLaunching) return;

    setIsLaunching(true);
    try {
      const result = await createScenario(trimmed);
      router.push(`/simulation/${result.scenario_id}`);
    } catch (err) {
      alert("Failed to start simulation.");
    } finally {
      setIsLaunching(false);
    }
  };

  const handleNextSlide = () => {
    setCarouselIndex((prev) => (prev + 1) % MOCK_SCENARIOS.length);
  };

  const handlePrevSlide = () => {
    setCarouselIndex((prev) => (prev - 1 + MOCK_SCENARIOS.length) % MOCK_SCENARIOS.length);
  };

  return (
    <main className="min-h-screen bg-black overflow-hidden font-sans select-none relative">
      {/* Dynamic particles background canvas */}
      <CanvasParticles />

      {/* ──────────────────────────────
          SECTION 1: HERO (ABOVE THE FOLD)
          ────────────────────────────── */}
      <section ref={heroRef} className="relative min-h-[90vh] flex flex-col items-center justify-center px-6 pt-16 pb-12 overflow-hidden border-b border-white/5 opacity-0">
        <HeroNebula />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[550px] h-[550px] ambient-glow pointer-events-none" />

        <div className="relative z-10 max-w-4xl text-center space-y-8 animate-fade-in-up mt-8">
          <img
            src="/logo.png"
            alt="Anamnesis-AI logo"
            className="mx-auto h-16 w-16 rounded-2xl border border-white/10 bg-slate-950/60 object-contain p-1.5 shadow-[0_0_40px_rgba(34,211,238,0.15)] backdrop-blur-md"
          />
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/5 bg-slate-950/60 px-4 py-1.5 backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400 font-mono">Parallel Timelines Research Portal</span>
          </div>

          <h1 className="bg-gradient-to-b from-slate-100 via-slate-200 to-slate-400 bg-clip-text text-5xl font-extrabold tracking-tight text-transparent sm:text-7xl leading-tight max-w-4xl mx-auto">
            Explore Alternate Realities
          </h1>
          <p className="mx-auto max-w-2xl text-sm text-slate-400 font-light leading-7 sm:text-md">
            Simulate how different decisions could reshape history, economics, climate, technology and society. Driven by a dedicated multi-agent reasoning cluster.
          </p>

          {/* Quick Scenario Launcher inside Hero */}
          <div className="mx-auto max-w-xl rounded-xl border border-white/10 bg-slate-950/50 p-2 shadow-2xl backdrop-blur-md flex items-center gap-2">
            <input
              type="text"
              placeholder="What if the Roman Empire never fell?"
              value={quickQuery}
              onChange={(e) => setQuickQuery(e.target.value)}
              className="flex-grow bg-transparent pl-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 outline-none"
            />
            <button
              type="button"
              onClick={handleQuickLaunch}
              disabled={!quickQuery.trim() || isLaunching}
              className="inline-flex h-9 items-center justify-center gap-1.5 rounded-lg bg-cyan-400 px-4 text-xs font-bold text-slate-950 hover:brightness-110 active:scale-[0.98] transition disabled:opacity-40"
            >
              {isLaunching ? (
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-950/30 border-t-slate-950" />
              ) : (
                <Play className="h-3 w-3 fill-slate-950" />
              )}
              <span className="hidden sm:inline">Simulate</span>
            </button>
          </div>

          <div className="flex items-center justify-center gap-4 text-xs font-bold uppercase tracking-wider pt-2">
            <Link href="/simulation" className="text-cyan-400 hover:text-cyan-300 transition flex items-center gap-1">
              Configure Detailed Setup <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </section>

      <InfiniteTimeline />

      {/* ──────────────────────────────
          SECTION 2: WHAT IS ANAMNESIS-AI?
          ────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 py-20 border-b border-white/5">
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="grid gap-12 lg:grid-cols-2 items-center"
        >
          <div className="space-y-4">
            <span className="text-mono-label text-cyan-400">Sandbox Philosophy</span>
            <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">What is Anamnesis-AI?</h2>
            <p className="text-sm text-slate-400 font-light leading-7">
              Anamnesis-AI is a premium, coordinate-mapping Alternate Reality simulator. Instead of producing generic AI text, the engine executes parallelized execution pathways. By using custom constraints, we evaluate the domino effect that one changed decision has across climate, trade, R&D, and cultural realignments.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-white/5 bg-[#070708] p-5 space-y-2">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 inline-block mb-1" />
              <h4 className="text-xs font-bold text-slate-200">Domain Dependency</h4>
              <p className="text-[11px] text-slate-400 leading-5 font-light">
                Our model ensures that a change in technology triggers matching, realistic shifts in labor demand and climate.
              </p>
            </div>
            <div className="rounded-xl border border-white/5 bg-[#070708] p-5 space-y-2">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-400 inline-block mb-1" />
              <h4 className="text-xs font-bold text-slate-200">Verified Databases</h4>
              <p className="text-[11px] text-slate-400 leading-5 font-light">
                RAG pipelines search historical records and arXiv studies to verify simulation boundaries.
              </p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ──────────────────────────────
          SECTION 3: HOW IT WORKS
          ────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 py-20 border-b border-white/5">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="space-y-12 text-center"
        >
          <div className="space-y-3">
            <span className="text-mono-label text-cyan-400">Workflow Pipeline</span>
            <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">How It Works</h2>
          </div>

          <div className="grid gap-4 md:grid-cols-5 text-left font-sans">
            {HOW_IT_WORKS.map((step) => (
              <div
                key={step.step}
                className="relative rounded-xl border border-white/5 bg-slate-950/35 p-5 shadow-xl transition-all duration-300 hover:border-white/10 group"
              >
                <div className="flex justify-between items-start mb-4">
                  <span className="font-mono text-2xl font-bold text-slate-800 group-hover:text-cyan-400/25 transition-colors">{step.step}</span>
                  <CheckCircle2 className="h-4 w-4 text-cyan-500/20 group-hover:text-cyan-400 transition-colors" />
                </div>
                <h3 className="mb-2 text-xs font-bold text-slate-200">{step.name}</h3>
                <p className="text-[11px] text-slate-400 leading-5 font-light">{step.desc}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* ──────────────────────────────
          SECTION 4: MEET THE AGENTS
          ────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 py-20 border-b border-white/5">
        <div className="grid gap-12 lg:grid-cols-3 items-center">
          <div className="lg:col-span-1 space-y-4">
            <span className="text-mono-label text-cyan-400">Collaboration Cluster</span>
            <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">Meet The Agents</h2>
            <p className="text-sm text-slate-400 font-light leading-7">
              Each specialized reasoning node processes a specific domain vector, communicating constraints to adjacent agents.
            </p>

            <div className="space-y-1 pt-4">
              {AGENT_SHOWCASE.map((agent) => {
                const isSelected = activeTab === agent.key;
                return (
                  <button
                    key={agent.key}
                    type="button"
                    onClick={() => setActiveTab(agent.key)}
                    className={`flex w-full items-center gap-3 rounded-lg border px-4 py-2.5 text-left text-xs font-semibold transition-all ${
                      isSelected
                        ? "border-cyan-500/25 bg-cyan-500/5 text-cyan-400"
                        : "border-transparent text-slate-500 hover:text-slate-200"
                    }`}
                  >
                    <span className={`h-1 w-1 rounded-full ${isSelected ? "bg-cyan-400" : "bg-transparent"}`} />
                    {agent.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="lg:col-span-2 rounded-2xl glass-panel p-8 sm:p-10 shadow-2xl relative overflow-hidden">
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <div className={`flex h-12 w-12 items-center justify-center rounded-xl border ${activeAgent.color}`}>
                  <ActiveIcon className="h-5.5 w-5.5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">{activeAgent.label}</h3>
                  <span className="text-[9px] uppercase font-bold tracking-widest text-slate-500">{activeAgent.focus}</span>
                </div>
              </div>

              <p className="text-xs text-slate-300 font-light leading-7">
                {activeAgent.description}
              </p>

              <div className="rounded-xl border border-white/5 bg-slate-950/60 p-5 space-y-2">
                <span className="text-[9px] uppercase font-bold tracking-widest text-cyan-400">Sample Insight Output</span>
                <p className="text-xs italic leading-6 text-slate-400">
                  &ldquo;{activeAgent.insight}&rdquo;
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ──────────────────────────────
          SECTION 5: EXAMPLE SIMULATIONS (CAROUSEL)
          ────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 py-20 border-b border-white/5">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="space-y-10"
        >
          <div className="flex items-end justify-between">
            <div className="space-y-2">
              <span className="text-mono-label text-cyan-400">Archive Vault</span>
              <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">Example Simulations</h2>
            </div>
            
            {/* Carousel navigation controls */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handlePrevSlide}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/5 bg-slate-950/50 text-slate-400 hover:text-white transition"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={handleNextSlide}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/5 bg-slate-950/50 text-slate-400 hover:text-white transition"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Carousel Slider Card */}
          <div className="relative overflow-hidden rounded-2xl border border-white/5 bg-slate-950/35 p-8 shadow-2xl relative min-h-[250px] flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase tracking-widest border-b border-white/5 pb-2">
                <span>{MOCK_SCENARIOS[carouselIndex].category} Simulation</span>
                <span>Seed Run</span>
              </div>
              <h3 className="text-lg font-bold text-white leading-snug">
                {MOCK_SCENARIOS[carouselIndex].title}
              </h3>
              <p className="text-xs text-slate-400 leading-6 font-light">
                {MOCK_SCENARIOS[carouselIndex].excerpt}
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between">
              <Link
                href={`/report/${MOCK_SCENARIOS[carouselIndex].id}`}
                className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-cyan-400 hover:text-cyan-300 transition-colors"
              >
                View Report Summary <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ──────────────────────────────
          SECTION 6: RESEARCH METHODOLOGY
          ────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 py-20 border-b border-white/5">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="space-y-10"
        >
          <div className="space-y-3">
            <span className="text-mono-label text-cyan-400">Vector Mappings</span>
            <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">Research Methodology</h2>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-xl border border-white/5 bg-[#070708] p-6 space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Context Seeding (RAG)</h3>
              <p className="text-xs text-slate-400 leading-6 font-light">
                Before simulation compilation, async loader loops pull context summaries from historical databases and arXiv publications, ensuring reasoning limits are mathematically structured.
              </p>
            </div>
            <div className="rounded-xl border border-white/5 bg-[#070708] p-6 space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Feedback Matrix</h3>
              <p className="text-xs text-slate-400 leading-6 font-light">
                The Narrator resolves differences between domain timelines, sorting events chronologically and mapping index outputs to radial dashboard scales.
              </p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ──────────────────────────────
          SECTION 7: WHY TRUST THE RESULTS
          ────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 py-20 border-b border-white/5">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="grid gap-12 lg:grid-cols-12 items-center"
        >
          <div className="lg:col-span-8 space-y-4">
            <span className="text-mono-label text-cyan-400">Plausibility Check</span>
            <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">Why Trust The Results?</h2>
            <p className="text-sm text-slate-400 font-light leading-7">
              Each simulation features a detailed audit log by the Critic agent. The Critic checks standard deviation limits of domain scores and identifies timeline contradictions. High-delta deviations drop the plausibility grade, giving researchers transparent logs of simulation limitations.
            </p>
          </div>

          <div className="lg:col-span-4 rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-6 space-y-2 text-cyan-300">
            <Shield className="h-6 w-6 text-cyan-400 mb-2" />
            <h4 className="text-xs font-bold uppercase tracking-wider">Consistency Graded</h4>
            <p className="text-[11px] leading-5 font-light text-slate-300">
              Confidence score decreases automatically if domain projections deviate from established socio-economic models.
            </p>
          </div>
        </motion.div>
      </section>

      {/* ──────────────────────────────
          SECTION 7.5: CONCLUSION
          ────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 py-20 border-b border-white/5">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="space-y-6"
        >
          <div className="space-y-3">
            <span className="text-mono-label text-cyan-400">Final Verdict</span>
            <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">Conclusion</h2>
          </div>
          <div className="space-y-3 border-l-2 border-cyan-500/40 pl-6">
            <p className="text-sm text-slate-300 font-light leading-7">
              History is not a single line — it is a lattice of decisions, each one waiting to be re-asked.
            </p>
            <p className="text-sm text-slate-300 font-light leading-7">
              Anamnesis-AI answers those questions with a disciplined swarm of specialist agents instead of a lone model's guess.
            </p>
            <p className="text-sm text-slate-300 font-light leading-7">
              Every projection is grounded in live research databases and audited by a Critic that grades its own plausibility.
            </p>
            <p className="text-sm text-slate-300 font-light leading-7">
              The result is an alternate timeline you can question, challenge, and trace back to its sources.
            </p>
          </div>
        </motion.div>
      </section>

      {/* ──────────────────────────────
          SECTION 8: CALL TO ACTION
          ────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-4xl px-6 py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="rounded-2xl border border-cyan-500/25 bg-slate-950 p-8 sm:p-12 text-center shadow-[0_0_50px_rgba(34,211,238,0.05)] space-y-6"
        >
          <h2 className="text-3xl font-extrabold text-white sm:text-4xl">Ready to Diverge History?</h2>
          <p className="mx-auto max-w-xl text-xs text-slate-400 font-light leading-6">
            Access our alternate reality workspace to seed and execute your own custom parallel historical projections.
          </p>

          <div>
            <Link
              href="/simulation"
              className="inline-flex h-10 items-center justify-center gap-1.5 rounded-lg bg-cyan-400 px-6 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:brightness-110 active:scale-[0.98]"
            >
              Run Custom Simulation <Play className="h-3 w-3 fill-slate-950" />
            </Link>
          </div>
        </motion.div>
      </section>
    </main>
  );
}

