"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import { Terminal as TerminalIcon, AlertTriangle, ArrowLeft, RefreshCw, Cpu } from "lucide-react";
import { getScenarioStatus } from "../../../lib/api";
import type { ScenarioStatusResponse } from "../../../lib/types";

const AGENTS = [
  { key: "historian", label: "Historian Agent", description: "Tracing divergence pivot points and chronological shifts." },
  { key: "economist", label: "Economist Agent", description: "Simulating labor transitions, trade flows, and GDP variance." },
  { key: "technology", label: "Technology Agent", description: "Projecting alternate hardware/software engineering paths." },
  { key: "society", label: "Society Agent", description: "Tracing vocational shifts, demographics, and cultural dynamics." },
  { key: "climate", label: "Climate Agent", description: "Modeling precipitation, carbon sequestration, and biodiversity." },
  { key: "political", label: "Political Agent", description: "Evaluating governance structures, sovereignty, and civic outcomes." },
  { key: "energy", label: "Energy Agent", description: "Modelling grids, resource capacity, and transition pathways." },
  { key: "healthcare", label: "Healthcare Agent", description: "Tracking public health systems, life expectancy, and care capacity." },
  { key: "demographics", label: "Demographics Agent", description: "Projecting population growth, urbanisation, and migration corridors." },
  { key: "critic", label: "Critic Agent", description: "Validating logic for internal timeline contradictions." }
];

const AGENT_LOGS: Record<string, string[]> = {
  historian: [
    "Historian │ Initializing alternate timeline graph...",
    "Historian │ Querying RAG database for historical baselines...",
    "Historian │ Divergence vector identified, branching nodes...",
    "Historian │ Tracing geopolitical border modifications...",
    "Historian │ Timeline events successfully resolved and persisted."
  ],
  climate: [
    "Climate   │ Booting climate feedback simulation mesh...",
    "Climate   │ Fetching atmospheric carbon baseline...",
    "Climate   │ Simulating precipitation shifts and regional cooling...",
    "Climate   │ Computing forestry biodiversity impact indices...",
    "Climate   │ Climate model complete. Output score formatted."
  ],
  economist: [
    "Economist │ Seeding macroeconomic equations...",
    "Economist │ Analyzing resource trade friction shifts...",
    "Economist │ Calculating white-collar labor transition rates...",
    "Economist │ Simulating sovereign wealth distribution changes...",
    "Economist │ Economic model calculations finalized."
  ],
  technology: [
    "Technology│ Scanning active computing blueprints...",
    "Technology│ Evaluating alternative material hardware constraints...",
    "Technology│ Simulating R&D trajectory shifts...",
    "Technology│ Analyzing energy grids and data center consumption...",
    "Technology│ Tech timeline vectors compiled."
  ],
  society: [
    "Society   │ Seeding community media cooperatives data...",
    "Society   │ Simulating vocational identity friction index...",
    "Society   │ Tracing global migration adjustments...",
    "Society   │ Projecting regional urbanization flows...",
    "Society   │ Social Realignment data validated."
  ],
  critic: [
    "Critic    │ Performing semantic audits across all outputs...",
    "Critic    │ Searching for timeline year contradictions...",
    "Critic    │ Grading assumptions and structural variances...",
    "Critic    │ Formulating risk logs and final confidence metrics...",
    "Critic    │ Consistency checks finished. Resolving to report."
  ]
};

export default function SimulationStatusPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [status, setStatus] = useState<ScenarioStatusResponse>({
    status: "pending",
    completed_agents: [],
    error_message: null
  });
  const [loadError, setLoadError] = useState("");
  const [consoleLogs, setConsoleLogs] = useState<string[]>(["[system] Initializing simulation workspace...", "[system] Connected to server. Preparing multi-agent pipeline..."]);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const id = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";

  // Auto scroll terminal to bottom
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [consoleLogs]);

  useEffect(() => {
    if (!id) return;

    let active = true;
    let intervalId: ReturnType<typeof setInterval> | undefined;
    let ws: WebSocket | undefined;

    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const wsBase = apiBase.replace(/^http/, "ws");
    const wsUrl = `${wsBase}/api/scenarios/${id}/ws`;

    // Establish WebSocket telemetry stream
    try {
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setConsoleLogs((l) => [...l, "[system] Connected to live agent telemetry channel."]);
      };
      
      ws.onmessage = (event) => {
        if (!active) return;
        setConsoleLogs((l) => [...l, event.data]);
      };
      
      ws.onerror = (err) => {
        console.error("WebSocket telemetry error:", err);
      };
      
      ws.onclose = () => {
        if (active) {
          setConsoleLogs((l) => [...l, "[system] Telemetry session closed."]);
        }
      };
    } catch (e) {
      console.error("Failed to connect websocket telemetry:", e);
    }

    const fetchStatus = async () => {
      try {
        const nextStatus = await getScenarioStatus(id);
        if (!active) return;

        setStatus(nextStatus);
        setLoadError("");

        if (nextStatus.status === "done") {
          if (intervalId) clearInterval(intervalId);
          if (ws) ws.close();
          setTimeout(() => {
            router.push(`/report/${id}`);
          }, 2000); // Small pause for user to read final terminal logs
        }

        if (nextStatus.status === "error") {
          if (intervalId) clearInterval(intervalId);
          if (ws) ws.close();
          setConsoleLogs((l) => [...l, `[error] Simulation aborted. Reason: ${nextStatus.error_message}`]);
        }
      } catch (err) {
        if (!active) return;
        setLoadError(err instanceof Error ? err.message : "Failed to load simulation status.");
      }
    };

    void fetchStatus();
    intervalId = setInterval(() => {
      void fetchStatus();
    }, 2000);

    return () => {
      active = false;
      if (intervalId) clearInterval(intervalId);
      if (ws) ws.close();
    };
  }, [id, router]);

  const completedAgents = status.completed_agents;

  return (
    <main className="min-h-screen bg-black px-4 sm:px-6 py-12 relative select-none">
      <div className="mx-auto max-w-7xl space-y-8">
        {/* Navigation / Header */}
        <div className="flex items-center justify-between">
          <Link
            href="/simulation"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to config
          </Link>
          <div className="flex items-center gap-2 text-mono-label text-slate-500">
            <Cpu className="h-3.5 w-3.5" />
            <span>Scenario ID: {id.slice(0, 8)}...</span>
          </div>
        </div>

        {/* Layout Grid */}
        <div className="grid gap-8 lg:grid-cols-12">
          {/* Left: Agents Status Cards */}
          <div className="lg:col-span-7 space-y-6">
            <div className="space-y-2">
              <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
                Research Pipeline
              </h1>
              <p className="text-xs text-slate-400 font-light">
                Monitoring live outputs and token exchanges from active reasoning layers.
              </p>
            </div>

            {status.status === "error" && (
              <div className="flex gap-3 rounded-xl border border-rose-500/25 bg-rose-500/5 p-5 animate-fade-in-up">
                <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-rose-200">Simulation Aborted</p>
                  <p className="text-xs text-rose-300/80 leading-5">
                    {status.error_message || loadError || "An unexpected processing error occurred."}
                  </p>
                </div>
              </div>
            )}

            <div className="space-y-3">
              {AGENTS.map((agent, idx) => {
                const isCompleted = completedAgents.includes(agent.key);
                const isCurrent =
                  status.status === "running" &&
                  !isCompleted &&
                  AGENTS.slice(0, idx).every((item) => completedAgents.includes(item.key));
                const isAborted = status.status === "error" && !isCompleted;

                let stateLabel = "Pending";
                let cardClass = "border-white/5 bg-slate-950/25 text-slate-500";
                let glowClass = "";

                if (isCompleted) {
                  stateLabel = "Completed";
                  cardClass = "border-emerald-500/20 bg-emerald-500/5 text-emerald-300";
                } else if (isCurrent) {
                  stateLabel = "Processing";
                  cardClass = "border-cyan-500/25 bg-cyan-500/5 text-cyan-200";
                  glowClass = "glow-pulse";
                } else if (isAborted) {
                  stateLabel = "Aborted";
                  cardClass = "border-rose-500/15 bg-rose-500/5 text-rose-400/60";
                }

                return (
                  <div
                    key={agent.key}
                    className={`flex items-center gap-4 rounded-xl border px-5 py-4 transition-all duration-300 ${cardClass} ${glowClass}`}
                  >
                    <div className="shrink-0 flex items-center justify-center">
                      {isCompleted ? (
                        <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
                      ) : isCurrent ? (
                        <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.5)] animate-ping" />
                      ) : (
                        <span className="h-2 w-2 rounded-full bg-slate-800" />
                      )}
                    </div>
                    <div className="min-w-0 flex-grow">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-white tracking-wide">{agent.label}</h4>
                        <span className="text-[9px] uppercase font-bold tracking-widest">{stateLabel}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 font-light leading-5">{agent.description}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: Scrolling Console Terminal */}
          <div className="lg:col-span-5 flex flex-col h-[520px] rounded-2xl border border-white/5 bg-[#070708] p-5 shadow-2xl">
            <div className="flex items-center gap-2 pb-3 border-b border-white/5 text-slate-400">
              <TerminalIcon className="h-4.5 w-4.5 text-cyan-400" />
              <span className="text-[10px] uppercase font-bold tracking-widest font-mono">Telemetry Logs</span>
            </div>

            <div className="flex-grow overflow-y-auto font-mono text-[10px] leading-5 text-slate-400 py-4 space-y-1">
              {consoleLogs.map((log, index) => {
                let colorClass = "text-slate-500";
                if (log.startsWith("[system]")) colorClass = "text-cyan-400";
                else if (log.startsWith("[error]")) colorClass = "text-rose-400";
                else if (log.includes("completed")) colorClass = "text-emerald-400";
                else if (log.includes("│")) colorClass = "text-slate-300";

                return (
                  <div key={index} className={colorClass}>
                    {log}
                  </div>
                );
              })}
              <div ref={terminalEndRef} />
            </div>

            <div className="pt-3 border-t border-white/5 flex items-center justify-between text-[9px] font-mono text-slate-600">
              <span>Streaming: {process.env.NEXT_PUBLIC_API_BASE_URL ? process.env.NEXT_PUBLIC_API_BASE_URL.replace(/^http/, "ws") : "ws://localhost:8000"}/api/scenarios/{id}/ws</span>
              {status.status === "running" && <RefreshCw className="h-3 w-3 animate-spin" />}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}