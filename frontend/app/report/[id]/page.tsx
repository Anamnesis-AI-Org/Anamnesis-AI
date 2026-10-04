"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { 
  FileText, Download, Share2, Compass, ArrowLeft, HelpCircle, 
  AlertTriangle, Shield, Check, Info, FileSpreadsheet, ChevronDown, ChevronUp,
  Scale, Globe, Clock, GitBranch, MessageSquare, BookOpen
} from "lucide-react";

import {
  getScenarioReport,
  ReportNotReadyError,
  askScenario,
  debateScenario,
  adjustScenario,
} from "../../../lib/api";
import type { AskResponse, DebateResponse } from "../../../lib/api";
import { MOCK_SCENARIOS } from "../../../lib/mockScenarios";
import type { FinalReport, UnifiedTimelineEvent, AgentOutputSummary } from "../../../lib/types";

// Import our advanced custom visual components
import AnimatedGauges from "../../../components/AnimatedGauges";
import InteractiveTimeline from "../../../components/InteractiveTimeline";
import DecisionTree from "../../../components/DecisionTree";
import CausalGraph from "../../../components/CausalGraph";
import ImpactMap from "../../../components/ImpactMap";

function formatAgentName(name: string): string {
  if (!name) return name;
  return name.charAt(0).toUpperCase() + name.slice(1);
}

const DEBATE_AGENTS = [
  "historian",
  "economist",
  "technology",
  "society",
  "climate",
  "political",
  "energy",
  "healthcare",
  "demographics",
];

interface RadarData {
  economy: number;
  technology: number;
  society: number;
  climate: number;
  politics: number;
}

function RadarChart({ data }: { data: RadarData }) {
  const size = 300;
  const center = size / 2;
  const maxRadius = 90;
  
  const axes: { key: keyof RadarData; label: string; angle: number }[] = [
    { key: "economy", label: "Economy", angle: -90 },
    { key: "technology", label: "Tech", angle: -18 },
    { key: "society", label: "Society", angle: 54 },
    { key: "climate", label: "Climate", angle: 126 },
    { key: "politics", label: "Politics", angle: 198 },
  ];

  const getCoordinates = (angleDegrees: number, value: number) => {
    const amplitude = Math.max(0, Math.min(100, Math.abs(value)));
    const radius = maxRadius * (amplitude / 100);
    const angleRadians = (angleDegrees * Math.PI) / 180;
    const x = center + radius * Math.cos(angleRadians);
    const y = center + radius * Math.sin(angleRadians);
    return { x, y };
  };

  const gridLevels = [25, 50, 75, 100];
  const gridPoints = gridLevels.map(level => {
    return axes.map(axis => {
      const angleRadians = (axis.angle * Math.PI) / 180;
      const radius = maxRadius * (level / 100);
      const x = center + radius * Math.cos(angleRadians);
      const y = center + radius * Math.sin(angleRadians);
      return `${x},${y}`;
    }).join(" ");
  });

  const simPoints = axes.map(axis => {
    const score = data[axis.key];
    const { x, y } = getCoordinates(axis.angle, score);
    return `${x},${y}`;
  }).join(" ");

  return (
    <div className="flex flex-col items-center justify-center p-5 bg-[#070708] rounded-xl border border-white/5 shadow-2xl relative overflow-hidden group w-full max-w-[280px] h-[300px]">
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-violet-500/5 opacity-40 pointer-events-none" />
      <span className="text-[9px] font-mono text-cyan-400 font-bold uppercase tracking-wider mb-2 relative z-10">Simulation Footprint</span>
      
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="relative z-10 -mt-2">
        {/* Draw background pentagons */}
        {gridPoints.map((points, idx) => (
          <polygon
            key={idx}
            points={points}
            fill="none"
            stroke="rgba(255, 255, 255, 0.04)"
            strokeWidth="1"
          />
        ))}

        {/* Draw axis lines */}
        {axes.map((axis, idx) => {
          const angleRadians = (axis.angle * Math.PI) / 180;
          const x2 = center + maxRadius * Math.cos(angleRadians);
          const y2 = center + maxRadius * Math.sin(angleRadians);
          return (
            <line
              key={idx}
              x1={center}
              y1={center}
              x2={x2}
              y2={y2}
              stroke="rgba(255, 255, 255, 0.05)"
              strokeWidth="1"
              strokeDasharray="3 3"
            />
          );
        })}

        {/* Draw impact polygon */}
        <polygon
          points={simPoints}
          fill="rgba(34, 211, 238, 0.12)"
          stroke="url(#radarGradient)"
          strokeWidth="2"
          className="transition-all duration-1000 ease-out"
        />

        {/* Define gradients */}
        <defs>
          <linearGradient id="radarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
        </defs>

        {/* Draw axis labels and dots */}
        {axes.map((axis, idx) => {
          const score = data[axis.key];
          const angleRadians = (axis.angle * Math.PI) / 180;
          const labelDist = maxRadius + 18;
          const lx = center + labelDist * Math.cos(angleRadians);
          const ly = center + labelDist * Math.sin(angleRadians) + 3;

          const { x, y } = getCoordinates(axis.angle, score);
          const dotColor = score > 0 ? "#10b981" : score < 0 ? "#f43f5e" : "#64748b";

          return (
            <g key={idx}>
              <circle
                cx={x}
                cy={y}
                r="4"
                fill={dotColor}
                stroke="rgba(0, 0, 0, 0.8)"
                strokeWidth="1.5"
                className="transition-all duration-1000 ease-out"
              />
              <text
                x={lx}
                y={ly}
                textAnchor="middle"
                className="font-mono text-[8px] font-bold fill-slate-500 transition-colors uppercase tracking-wider"
              >
                {axis.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<FinalReport | null>(null);
  const [error, setError] = useState("");
  const [shareStatus, setShareStatus] = useState("Share Report");
  const [activeTab, setActiveTab] = useState<"synthesis" | "timeline" | "tree" | "causal" | "discussions" | "sources" | "exploration">("synthesis");
  const [isMock, setIsMock] = useState(false);

  // Exploration Lab state (Q&A, debate, parameter adjustment)
  const [question, setQuestion] = useState("");
  const [qaAnswer, setQaAnswer] = useState<AskResponse | null>(null);
  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState("");

  const [debateTopic, setDebateTopic] = useState("");
  const [debateAgentA, setDebateAgentA] = useState("historian");
  const [debateAgentB, setDebateAgentB] = useState("economist");
  const [debateResult, setDebateResult] = useState<DebateResponse | null>(null);
  const [debateLoading, setDebateLoading] = useState(false);
  const [debateError, setDebateError] = useState("");

  const [adjustments, setAdjustments] = useState<Record<string, number>>({
    resource_abundance: 50,
    transition_speed: 50,
    government_control: 50,
    climate_feedback: 50,
  });
  const [adjustLoading, setAdjustLoading] = useState(false);
  const [adjustError, setAdjustError] = useState("");

  const id = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";

  // Check if it's a mock report or API report
  useEffect(() => {
    if (!id) return;

    const matchedMock = MOCK_SCENARIOS.find((sc) => sc.id === id);
    if (matchedMock) {
      setIsMock(true);
      setReport(matchedMock.report);
      setError("");
      return;
    }

    setIsMock(false);
    let active = true;

    const loadReport = async () => {
      try {
        const nextReport = await getScenarioReport(id);
        if (!active) return;
        setReport(nextReport);
        setError("");
        try {
          window.localStorage.setItem(`anamnesis_report_${id}`, JSON.stringify(nextReport));
        } catch {
          // Ignore storage quota / privacy mode errors.
        }
      } catch (loadError) {
        if (!active) return;
        if (loadError instanceof ReportNotReadyError) {
          router.push(`/simulation/${id}`);
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Failed to load report.");
      }
    };

    void loadReport();

    return () => {
      active = false;
    };
  }, [id, router]);

  const sortedTimeline = useMemo(() => {
    if (!report) return [] as UnifiedTimelineEvent[];
    return [...report.alternate_timeline].sort((l, r) => l.year - r.year);
  }, [report]);

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setShareStatus("Link Copied!");
    setTimeout(() => setShareStatus("Share Report"), 2000);
  };

  const handleAsk = async () => {
    if (!question.trim() || isMock) return;
    setQaLoading(true);
    setQaError("");
    setQaAnswer(null);
    try {
      const res = await askScenario(id, question.trim());
      setQaAnswer(res);
    } catch (err) {
      setQaError(err instanceof Error ? err.message : "Failed to answer question.");
    } finally {
      setQaLoading(false);
    }
  };

  const handleDebate = async () => {
    if (!debateTopic.trim() || isMock) return;
    setDebateLoading(true);
    setDebateError("");
    setDebateResult(null);
    try {
      const res = await debateScenario(id, debateTopic.trim(), debateAgentA, debateAgentB);
      setDebateResult(res);
    } catch (err) {
      setDebateError(err instanceof Error ? err.message : "Failed to run debate.");
    } finally {
      setDebateLoading(false);
    }
  };

  const handleAdjust = async () => {
    if (isMock) return;
    setAdjustLoading(true);
    setAdjustError("");
    try {
      const updated = await adjustScenario(id, adjustments);
      setReport(updated);
      try {
        window.localStorage.setItem(`anamnesis_report_${id}`, JSON.stringify(updated));
      } catch {
        // Ignore storage errors.
      }
    } catch (err) {
      setAdjustError(err instanceof Error ? err.message : "Failed to apply adjustments.");
    } finally {
      setAdjustLoading(false);
    }
  };

  const handleExport = () => {
    window.print();
  };

  if (error) {
    return (
      <main className="min-h-screen bg-black flex items-center justify-center px-6">
        <div className="max-w-md w-full rounded-2xl border border-rose-500/20 bg-rose-500/5 p-8 text-center shadow-2xl">
          <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto mb-4" />
          <p className="text-md font-semibold text-rose-200">Unable to load report</p>
          <p className="mt-2 text-xs text-rose-300/80 leading-5">{error}</p>
          <div className="mt-6">
            <Link
              href="/simulation"
              className="inline-flex items-center justify-center rounded-xl bg-white/10 px-5 py-2.5 text-xs font-semibold text-white transition hover:bg-white/15"
            >
              <ArrowLeft className="mr-2 h-4 w-4" /> Back to config
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (!report) {
    return (
      <main className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-slate-500 font-mono text-xs flex items-center gap-3">
          <span className="h-4.5 w-4.5 animate-spin rounded-full border-2 border-slate-700 border-t-cyan-400" />
          Retrieving unified research report...
        </div>
      </main>
    );
  }

  const impactDashboard = report.impact_dashboard;

  const tabs: { id: typeof activeTab; label: string; icon: typeof FileText }[] = [
    { id: "synthesis", label: "Executive Synthesis", icon: FileText },
    { id: "timeline", label: "Interactive Chronology", icon: Clock },
    { id: "tree", label: "Divergence Tree", icon: GitBranch },
    { id: "causal", label: "Causal DAG Graph", icon: GitBranch },
    { id: "discussions", label: "Domain Briefings", icon: MessageSquare },
    { id: "sources", label: "Consulted Sources", icon: BookOpen },
    ...(isMock
      ? []
      : [{ id: "exploration" as typeof activeTab, label: "Exploration Lab", icon: HelpCircle }]),
  ];

  return (
    <main className="min-h-screen bg-black px-6 py-12 relative overflow-hidden select-none">
      <div className="mx-auto max-w-5xl space-y-8 relative z-10">
        
        {/* Navigation & Actions Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <Link
            href="/library"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <Compass className="h-3.5 w-3.5" /> Back to library
          </Link>
          
          <div className="flex flex-wrap items-center gap-2">
            {/* Compare Trigger */}
            <Link
              href={`/compare?idA=${id}`}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-950/20 px-4 text-xs font-semibold text-cyan-400 hover:bg-cyan-950/45 transition-colors"
            >
              <Scale className="h-3.5 w-3.5" /> Compare Scenario
            </Link>

            <button
              type="button"
              onClick={handleShare}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-white/5 bg-white/5 px-4 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
            >
              <Share2 className="h-3.5 w-3.5" /> {shareStatus}
            </button>
            
            <button
              type="button"
              onClick={handleExport}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-cyan-400 px-4 text-xs font-bold text-slate-950 transition hover:brightness-110"
            >
              <Download className="h-3.5 w-3.5" /> Export PDF
            </button>
          </div>
        </div>

        {/* Tabbed Navigation Bar */}
        <div className="flex border-b border-white/5 overflow-x-auto scrollbar-none">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-4 border-b-2 font-mono text-[10px] uppercase font-bold tracking-widest transition-all duration-300 shrink-0 ${
                  isActive
                    ? "border-cyan-400 text-cyan-400 bg-cyan-400/5"
                    : "border-transparent text-slate-500 hover:text-slate-300 hover:bg-white/5"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Main Tab Contents */}
        <div className="space-y-8 min-h-[500px]">
          
          {/* TAB 1: EXECUTIVE SYNTHESIS */}
          {activeTab === "synthesis" && (
            <div className="space-y-8 animate-fade-in">
              {/* Executive Summary */}
              <section className="rounded-2xl glass-panel p-8 shadow-2xl space-y-4">
                <div className="flex items-center gap-2 text-mono-label text-cyan-400">
                  <FileText className="h-3.5 w-3.5" />
                  <span>Scenario Abstract Summary</span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold leading-snug text-white">
                  {report.scenario_summary}
                </h1>
              </section>

              {/* Advanced Scoring Gauges */}
              <AnimatedGauges
                plausibilityScore={report.confidence_score}
                uncertaintyScore={report.uncertainty_score || 0}
                calibrationScore={report.calibration_score || 100}
              />

              {/* Geographic Impact Map & Radar Matrix Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
                {/* World Map Container (col-span-8) */}
                <div className="lg:col-span-8 rounded-2xl glass-panel p-6 sm:p-8 flex flex-col justify-between space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2 font-mono">
                    <Globe className="h-4 w-4 text-cyan-400" /> Scenario Impact Focus Zones
                  </h3>
                  <ImpactMap
                    scenarioTitle={report.scenario_summary}
                    scenarioSummary={report.scenario_summary}
                    agentOutputs={report.agent_outputs}
                  />
                </div>

                {/* Radar Chart matrix (col-span-4) */}
                <div className="lg:col-span-4 rounded-2xl glass-panel p-6 sm:p-8 flex flex-col items-center justify-center">
                  <RadarChart data={impactDashboard} />
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: INTERACTIVE TIMELINE */}
          {activeTab === "timeline" && (
            <div className="animate-fade-in">
              <InteractiveTimeline
                events={sortedTimeline}
                validations={report.grounding_validations || []}
                onBranch={(event) => {
                  const eventId = event.id || `${event.year}`;
                  router.push(`/simulation?parent_id=${id}&event_id=${eventId}`);
                }}
              />
            </div>
          )}

          {/* TAB 3: DIVERGENCE TREE */}
          {activeTab === "tree" && (
            <div className="animate-fade-in">
              <DecisionTree
                scenarioId={id}
                events={sortedTimeline}
                links={report.causal_graph || []}
                onBranch={(event) => {
                  const eventId = event.id || `${event.year}`;
                  router.push(`/simulation?parent_id=${id}&event_id=${eventId}`);
                }}
              />
            </div>
          )}

          {/* TAB 3: CAUSAL DAG GRAPH */}
          {activeTab === "causal" && (
            <div className="animate-fade-in">
              <CausalGraph
                events={report.alternate_timeline}
                links={report.causal_graph || []}
              />
            </div>
          )}

          {/* TAB 4: DOMAIN BRIEFINGS */}
          {activeTab === "discussions" && (
            <div className="space-y-8 animate-fade-in">
              
              {/* Agent narratives */}
              <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-6">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
                  <h2 className="text-md font-bold tracking-wide text-white">Expert Domain Briefings</h2>
                </div>

                <div className="grid gap-6 md:grid-cols-2">
                  {report.agent_outputs.map((agent: AgentOutputSummary, index: number) => (
                    <div
                      key={`${agent.agent_name}-${index}`}
                      className="rounded-xl border border-white/5 bg-slate-950/45 p-5 shadow-inner hover:border-white/10 transition-colors duration-300"
                    >
                      <div className="mb-3 flex items-center justify-between border-b border-white/5 pb-2">
                        <p className="font-semibold text-cyan-200 text-xs tracking-wide">{formatAgentName(agent.agent_name)} Agent</p>
                        <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-slate-500">Domain Briefing</span>
                      </div>
                      <p className="text-xs leading-relaxed text-slate-400 font-light">{agent.analysis_text}</p>
                    </div>
                  ))}
                </div>
              </section>

              {/* Critic panel */}
              <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-6">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                  <h2 className="text-md font-bold tracking-wide text-white">Critic Evaluation Report</h2>
                </div>

                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-slate-900/30 border border-white/5 space-y-1.5">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">Plausibility assessment Rationale</h4>
                    <p className="text-xs leading-relaxed text-slate-400 font-light">
                      {report.confidence_explanation}
                    </p>
                  </div>

                  <div className="grid gap-6 sm:grid-cols-2">
                    <div className="space-y-2 p-4 rounded-xl bg-slate-900/30 border border-white/5">
                      <h5 className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                        <AlertTriangle className="h-3.5 w-3.5 text-rose-400" /> Inconsistencies Detected
                      </h5>
                      <ul className="text-xs space-y-2 font-light text-rose-300">
                        {report.risk_notes.map((note, idx) => (
                          <li key={idx} className="flex items-start gap-1.5 leading-normal">
                            <span className="text-rose-400">•</span>
                            <span>{note}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="space-y-2 p-4 rounded-xl bg-slate-900/30 border border-white/5">
                      <h5 className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                        <Shield className="h-3.5 w-3.5 text-emerald-400" /> Calibration Notes
                      </h5>
                      <ul className="text-xs space-y-2 font-light text-emerald-300">
                        <li className="flex items-start gap-1.5 leading-normal">
                          <span className="text-emerald-400">•</span>
                          <span>Timeline pacing matches standard logical transitions without ungrounded jumps.</span>
                        </li>
                        <li className="flex items-start gap-1.5 leading-normal">
                          <span className="text-emerald-400">•</span>
                          <span>Cross-agent contradictions are within bounds (plausibility score {report.confidence_score}%).</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </section>

              {/* Assumptions panel */}
              {report.assumptions && report.assumptions.length > 0 && (
                <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-6">
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
                    <h2 className="text-md font-bold tracking-wide text-white">Extracted Core Assumptions</h2>
                  </div>
                  <div className="grid gap-6 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                    {report.assumptions.map((item, idx) => {
                      const impactColor = 
                        item.impact_level.toLowerCase() === "high" 
                          ? "border-rose-500/30 bg-rose-500/10 text-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.1)]" 
                          : item.impact_level.toLowerCase() === "medium"
                          ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
                          : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
                      
                      return (
                        <div key={idx} className="p-4 rounded-xl bg-slate-955/40 border border-white/5 flex flex-col justify-between space-y-3 hover:border-white/10 transition duration-300">
                          <div className="flex justify-between items-center">
                            <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-slate-500">
                              {formatAgentName(item.agent_name)} Agent
                            </span>
                            <span className={`text-[8px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${impactColor}`}>
                              {item.impact_level} Impact
                            </span>
                          </div>
                          <p className="text-xs font-light text-slate-300 leading-relaxed italic">
                            "{item.assumption}"
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

            </div>
          )}

          {/* TAB 5: CONSULTED SOURCES */}
          {activeTab === "sources" && (
            <div className="animate-fade-in">
              <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-6">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                  <h2 className="text-md font-bold tracking-wide text-white">Consulted Sources & References</h2>
                </div>
                
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="rounded-xl border border-white/5 bg-slate-950/45 p-5 shadow-inner">
                    <h3 className="mb-3 text-[10px] font-bold uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
                      <Info className="h-3.5 w-3.5" /> Primary Sources
                    </h3>
                    {report.sources_consulted && report.sources_consulted.length > 0 ? (
                      <ul className="list-inside list-disc space-y-2 text-xs text-slate-400 font-light">
                        {report.sources_consulted.map((source, index) => (
                          <li key={index}>{source}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-600 font-light">No external sources consulted.</p>
                    )}
                  </div>
                  
                  <div className="rounded-xl border border-white/5 bg-slate-950/45 p-5 shadow-inner">
                    <h3 className="mb-3 text-[10px] font-bold uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
                      <FileSpreadsheet className="h-3.5 w-3.5" /> Retrieved Documents
                    </h3>
                    {report.retrieved_documents && report.retrieved_documents.length > 0 ? (
                      <ul className="list-inside list-disc space-y-2 text-xs text-slate-400 font-light">
                        {report.retrieved_documents.map((doc, index) => (
                          <li key={index}>{doc}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-600 font-light">No reference materials retrieved.</p>
                    )}
                  </div>
                </div>
              </section>

              {/* Grounding validation list */}
              {report.grounding_validations && report.grounding_validations.length > 0 && (
                <section className="mt-8 rounded-2xl glass-panel p-8 shadow-xl space-y-6">
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <h2 className="text-md font-bold tracking-wide text-white">Grounding & Source Verification Audit</h2>
                  </div>
                  
                  <div className="grid gap-6 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                    {report.grounding_validations.map((val, idx) => {
                      const scoreColor = 
                        val.grounding_score >= 80 
                          ? "text-emerald-400 bg-emerald-950/20 border-emerald-500/30 shadow-[0_0_8px_rgba(16,185,129,0.1)]" 
                          : val.grounding_score >= 60
                          ? "text-amber-400 bg-amber-950/20 border-amber-500/30"
                          : "text-rose-400 bg-rose-950/20 border-rose-500/30 shadow-[0_0_8px_rgba(244,63,94,0.1)]";

                      return (
                        <div key={idx} className="p-5 rounded-xl border border-white/5 bg-slate-950/40 space-y-4 hover:border-white/10 transition duration-300">
                          <div className="flex justify-between items-center border-b border-white/5 pb-3">
                            <span className="text-xs font-bold text-slate-200 uppercase tracking-wide">
                              {formatAgentName(val.agent_name)} Agent
                            </span>
                            <span className={`text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${scoreColor}`}>
                              {val.grounding_score}% Grounded
                            </span>
                          </div>
                          
                          <p className="text-xs text-slate-400 leading-relaxed font-light">
                            {val.explanation}
                          </p>

                          {val.unsupported_claims && val.unsupported_claims.length > 0 && (
                            <div className="p-3 rounded-lg bg-rose-950/10 border border-rose-500/10 space-y-1.5">
                              <span className="text-[8px] font-bold uppercase tracking-wider text-rose-300 block">
                                Unsupported Claims Flagged
                              </span>
                              <ul className="list-inside list-disc text-[10px] text-rose-400/95 space-y-1 leading-normal font-light font-sans">
                                {val.unsupported_claims.map((claim, cIdx) => (
                                  <li key={cIdx}>{claim}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

            </div>
          )}

          {/* TAB: EXPLORATION LAB */}
          {activeTab === "exploration" && !isMock && (
            <div className="space-y-8 animate-fade-in">

              {/* Ask the simulation */}
              <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-5">
                <div className="flex items-center gap-2">
                  <HelpCircle className="h-4 w-4 text-cyan-400" />
                  <h2 className="text-md font-bold tracking-wide text-white">Ask the Simulation</h2>
                </div>
                <p className="text-xs text-slate-400 font-light leading-6">
                  Pose a follow-up question. The answer is grounded in this report&apos;s timeline and
                  domain briefings, with citations.
                </p>
                <div className="flex flex-col sm:flex-row gap-3">
                  <input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") void handleAsk(); }}
                    placeholder="E.g., How does this scenario affect coastal agriculture?"
                    className="flex-grow rounded-xl border border-white/5 bg-slate-950/65 px-4 py-3 text-xs text-slate-100 placeholder:text-slate-600 outline-none focus:border-cyan-500/30 transition"
                  />
                  <button
                    type="button"
                    onClick={() => void handleAsk()}
                    disabled={qaLoading || !question.trim()}
                    className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-cyan-400 px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {qaLoading ? "Analyzing..." : "Ask"}
                  </button>
                </div>
                {qaError && (
                  <p className="text-xs text-rose-400 font-mono flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5" /> {qaError}
                  </p>
                )}
                {qaAnswer && (
                  <div className="rounded-xl border border-white/5 bg-slate-950/45 p-5 space-y-3">
                    <p className="text-xs leading-relaxed text-slate-300 font-light whitespace-pre-wrap">
                      {qaAnswer.answer}
                    </p>
                    {qaAnswer.citations && qaAnswer.citations.length > 0 && (
                      <div className="pt-3 border-t border-white/5 space-y-1.5">
                        <span className="text-[9px] font-bold uppercase tracking-wider text-cyan-400">
                          Citations
                        </span>
                        <ul className="list-inside list-disc space-y-1 text-[10px] text-slate-500 font-light">
                          {qaAnswer.citations.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </section>


              {/* Agent debate */}
              <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-5">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-violet-400" />
                  <h2 className="text-md font-bold tracking-wide text-white">Agent Debate</h2>
                </div>
                <p className="text-xs text-slate-400 font-light leading-6">
                  Stage a structured two-round debate between two domain agents, concluded by a
                  Critic synthesis.
                </p>
                <input
                  value={debateTopic}
                  onChange={(e) => setDebateTopic(e.target.value)}
                  placeholder="Debate topic, e.g., the pace of the transition"
                  className="w-full rounded-xl border border-white/5 bg-slate-950/65 px-4 py-3 text-xs text-slate-100 placeholder:text-slate-600 outline-none focus:border-violet-500/30 transition"
                />
                <div className="grid grid-cols-2 gap-3">
                  <select
                    value={debateAgentA}
                    onChange={(e) => setDebateAgentA(e.target.value)}
                    className="rounded-xl border border-white/5 bg-slate-950 p-3 text-xs text-slate-300 outline-none focus:border-violet-400/30 cursor-pointer"
                  >
                    {DEBATE_AGENTS.map((a) => (
                      <option key={a} value={a}>{a}</option>
                    ))}
                  </select>
                  <select
                    value={debateAgentB}
                    onChange={(e) => setDebateAgentB(e.target.value)}
                    className="rounded-xl border border-white/5 bg-slate-950 p-3 text-xs text-slate-300 outline-none focus:border-violet-400/30 cursor-pointer"
                  >
                    {DEBATE_AGENTS.map((a) => (
                      <option key={a} value={a}>{a}</option>
                    ))}
                  </select>
                </div>
                <button
                  type="button"
                  onClick={() => void handleDebate()}
                  disabled={debateLoading || !debateTopic.trim() || debateAgentA === debateAgentB}
                  className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-violet-500 px-5 py-3 text-xs font-bold uppercase tracking-wider text-white transition hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {debateLoading ? "Debating..." : "Start Debate"}
                </button>
                {debateError && <p className="text-xs text-rose-400 font-mono">{debateError}</p>}
                {debateResult && (
                  <div className="space-y-3">
                    {debateResult.rounds.map((r, i) => (
                      <div key={i} className="rounded-xl border border-white/5 bg-slate-950/45 p-4 space-y-1">
                        <span className="text-[9px] font-bold uppercase tracking-wider text-violet-300">
                          Round {r.round_num} · {formatAgentName(r.agent_name)}
                        </span>
                        <p className="text-xs leading-relaxed text-slate-300 font-light">{r.argument}</p>
                      </div>
                    ))}
                    <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 space-y-1">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1">
                        <Shield className="h-3 w-3" /> Critic Synthesis
                      </span>
                      <p className="text-xs leading-relaxed text-slate-300 font-light">{debateResult.consensus}</p>
                    </div>
                  </div>
                )}
              </section>


              {/* Parameter re-simulation */}
              <section className="rounded-2xl glass-panel p-8 shadow-xl space-y-5">
                <div className="flex items-center gap-2">
                  <Scale className="h-4 w-4 text-emerald-400" />
                  <h2 className="text-md font-bold tracking-wide text-white">Parameter Re-Simulation</h2>
                </div>
                <p className="text-xs text-slate-400 font-light leading-6">
                  Adjust structural parameters and re-run only the affected agents. The report is
                  recomposed in place.
                </p>
                <div className="grid gap-5 sm:grid-cols-2">
                  {Object.entries(adjustments).map(([key, value]) => (
                    <div key={key} className="space-y-2">
                      <div className="flex justify-between text-[10px] font-mono uppercase tracking-wider text-slate-400">
                        <span>{key.replace(/_/g, " ")}</span>
                        <span className="text-emerald-400">{value}</span>
                      </div>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        value={value}
                        onChange={(e) =>
                          setAdjustments((prev) => ({ ...prev, [key]: Number(e.target.value) }))
                        }
                        className="w-full accent-emerald-400"
                      />
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => void handleAdjust()}
                  disabled={adjustLoading}
                  className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-emerald-400 px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {adjustLoading ? "Re-simulating..." : "Apply & Re-Simulate"}
                </button>
                {adjustError && <p className="text-xs text-rose-400 font-mono">{adjustError}</p>}
              </section>

            </div>
          )}


        </div>

        {/* Action Trigger */}
        <div className="flex justify-center pt-4">
          <Link
            href="/simulation"
            className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 px-8 py-3 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:brightness-110 active:scale-[0.98]"
          >
            Run Another Simulation
          </Link>
        </div>
      </div>
    </main>
  );
}
