"use client";

import { useCallback, useRef, useState } from "react";
import {
  createProject,
  formatApiError,
  getExportZipUrl,
  runAgent,
  runAllAgents,
  type AgentKey,
  type PipelineState,
  type PipelineStatus,
  type Project,
} from "@/lib/api";
import BusinessView from "./BusinessView";
import PRDView from "./PRDView";
import ArchitectureView from "./ArchitectureView";
import TasksView from "./TasksView";

const AGENTS: { key: AgentKey; label: string }[] = [
  { key: "business", label: "Business Analyst" },
  { key: "product", label: "Product Manager" },
  { key: "architect", label: "Architect" },
  { key: "planner", label: "Engineering Planner" },
];

const AGENT_ORDER: AgentKey[] = ["business", "product", "architect", "planner"];

function initialPipelineStatus(): PipelineStatus {
  return { business: "pending", product: "pending", architect: "pending", planner: "pending" };
}

const AGENT_ICON: Record<string, string> = {
  pending: "\u23F3",
  running: "\uD83D\uDD04",
  complete: "\u2705",
  error: "\u274C",
};

type ExportFormat = "markdown" | "html" | "mermaid";

const EXPORT_FORMATS: { value: ExportFormat; label: string; icon: string }[] = [
  { value: "markdown", label: "Markdown", icon: "\uD83D\uDCC4" },
  { value: "html", label: "HTML Report", icon: "\uD83C\uDF10" },
  { value: "mermaid", label: "Architecture Diagram", icon: "\uD83D\uDD0C" },
];

export default function ControlPanel() {
  const [idea, setIdea] = useState("");
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState<AgentKey | "create" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pipelineState, setPipelineState] = useState<PipelineState>("idle");
  const [agentStatus, setAgentStatus] = useState<PipelineStatus>(initialPipelineStatus);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat>("markdown");
  const [showRawJson, setShowRawJson] = useState(false);
  const projectRef = useRef(project);
  projectRef.current = project;

  const isBusy = loading !== null || pipelineRunning;

  const handleRunAll = useCallback(() => {
    if (!project) return;
    setError(null);
    setPipelineRunning(true);
    setPipelineState("running");
    setAgentStatus(initialPipelineStatus());

    runAllAgents(project.id, {
      onAgentStart(agent) {
        setAgentStatus((prev) => ({ ...prev, [agent]: "running" }));
      },
      onAgentComplete(agent) {
        setAgentStatus((prev) => ({ ...prev, [agent]: "complete" }));
      },
      onAgentError(agent, errMsg) {
        setAgentStatus((prev) => ({ ...prev, [agent]: "error" }));
        setError(errMsg);
        setPipelineState("partial_failure");
        setPipelineRunning(false);
      },
      onComplete(updated) {
        setProject(updated);
        setPipelineState("complete");
        setPipelineRunning(false);
      },
      onError(msg) {
        setError(msg);
        setPipelineState("partial_failure");
        setPipelineRunning(false);
      },
    });
  }, [project]);

  async function handleCreate() {
    if (!idea.trim()) return;
    setLoading("create");
    setError(null);
    try {
      const p = await createProject(idea.trim());
      setProject(p);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(null);
    }
  }

  async function handleRunAgent(agent: AgentKey) {
    if (!project) return;
    setLoading(agent);
    setError(null);
    try {
      const p = await runAgent(project.id, agent);
      setProject(p);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(null);
    }
  }

  async function handleRetryFromFailed() {
    if (!project) return;
    setError(null);
    setPipelineRunning(true);
    setPipelineState("running");

    const p = projectRef.current;
    if (!p) return;

    for (const agent of AGENT_ORDER) {
      const status = agentStatus[agent];
      if (status === "complete") continue;
      setAgentStatus((prev) => ({ ...prev, [agent]: "running" }));
      try {
        const updated = await runAgent(p.id, agent);
        setProject(updated);
        projectRef.current = updated;
        setAgentStatus((prev) => ({ ...prev, [agent]: "complete" }));
      } catch (e) {
        setAgentStatus((prev) => ({ ...prev, [agent]: "error" }));
        setError(formatApiError(e));
        setPipelineState("partial_failure");
        setPipelineRunning(false);
        return;
      }
    }
    setPipelineState("complete");
    setPipelineRunning(false);
  }

  async function handleDownload() {
    if (!project) return;
    const url = getExportZipUrl(project.id, exportFormat);
    const a = document.createElement("a");
    a.href = url;
    a.download = `project-${project.id.slice(0, 8)}-${exportFormat}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  const getCompletedCount = () =>
    AGENT_ORDER.filter((k) => agentStatus[k] === "complete").length;

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <img src="/logo.svg" alt="AI Project CTO" style={styles.logo} />
        <p style={styles.subtitle}>
          Multi-agent workflow — transform an idea into structured project artifacts
        </p>
      </header>

      <section style={styles.section}>
        <label style={styles.label} htmlFor="idea">
          Project Idea
        </label>
        <textarea
          id="idea"
          style={styles.textarea}
          rows={3}
          placeholder="I want to build AI Resume SaaS"
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
        />
        <button
          style={styles.primaryBtn}
          onClick={handleCreate}
          disabled={isBusy || !idea.trim()}
        >
          {loading === "create" ? "Creating\u2026" : "Create Project"}
        </button>
      </section>

      {project && (
        <section style={styles.section}>
          <p style={styles.meta}>
            Project ID: <code>{project.id}</code>
          </p>

          <button
            style={styles.runAllBtn}
            onClick={handleRunAll}
            disabled={isBusy}
          >
            {pipelineState === "running" ? "Running All\u2026" : "Run All Agents"}
          </button>

          {pipelineState !== "idle" && (
            <div style={styles.pipelineProgress}>
              {AGENT_ORDER.map((key) => {
                const status = agentStatus[key];
                return (
                  <span key={key} style={styles.pipelineItem}>
                    <span style={styles.pipelineIcon}>{AGENT_ICON[status]}</span>
                    <span style={styles.pipelineLabel}>{AGENTS.find((a) => a.key === key)?.label}</span>
                  </span>
                );
              })}
            </div>
          )}

          {pipelineState === "partial_failure" && (
            <button
              style={styles.retryBtn}
              onClick={handleRetryFromFailed}
              disabled={isBusy}
            >
              {pipelineRunning ? "Retrying\u2026" : `Retry from Failed (${getCompletedCount()}/4 done)`}
            </button>
          )}

          <div style={styles.agentRow}>
            {AGENTS.map(({ key, label }) => (
              <button
                key={key}
                style={styles.agentBtn}
                onClick={() => handleRunAgent(key)}
                disabled={isBusy}
              >
                {loading === key ? "Running\u2026" : `Run ${label}`}
              </button>
            ))}
          </div>

          <div style={styles.exportRow}>
            <select
              style={styles.formatSelect}
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
              disabled={isBusy}
            >
              {EXPORT_FORMATS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.icon} {f.label}
                </option>
              ))}
            </select>
            <button
              style={styles.downloadBtn}
              onClick={handleDownload}
              disabled={isBusy}
            >
              Download Export
            </button>
          </div>
        </section>
      )}

      {error && <p style={styles.error}>{error}</p>}

      {project && (
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>Project Artifacts</h2>
            <button
              style={styles.toggleJsonBtn}
              onClick={() => setShowRawJson(!showRawJson)}
            >
              {showRawJson ? "Hide Raw JSON" : "Show Raw JSON"}
            </button>
          </div>

          {/* Structured views */}
          {project.business_analysis && !showRawJson && (
            <div style={styles.artifactCard}>
              <h3 style={styles.artifactTitle}>Business Analysis</h3>
              <BusinessView data={project.business_analysis} />
            </div>
          )}
          {project.prd && !showRawJson && (
            <div style={styles.artifactCard}>
              <h3 style={styles.artifactTitle}>Product Requirements (PRD)</h3>
              <PRDView data={project.prd} />
            </div>
          )}
          {project.architecture && !showRawJson && (
            <div style={styles.artifactCard}>
              <h3 style={styles.artifactTitle}>Architecture</h3>
              <ArchitectureView data={project.architecture} />
            </div>
          )}
          {project.tasks && !showRawJson && (
            <div style={styles.artifactCard}>
              <h3 style={styles.artifactTitle}>Implementation Tasks</h3>
              <TasksView data={project.tasks} />
            </div>
          )}

          {/* Raw JSON (collapsible) */}
          {(showRawJson || !showRawJson && !project.business_analysis && !project.prd && !project.architecture && !project.tasks) && (
            <pre style={styles.json}>{JSON.stringify(project, null, 2)}</pre>
          )}
        </section>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: 900,
    margin: "0 auto",
    padding: "2rem 1.5rem",
    fontFamily: "system-ui, -apple-system, sans-serif",
    color: "#e2e8f0",
    background: "#0f172a",
    minHeight: "100vh",
  },
  header: { marginBottom: "2rem" },
  logo: { height: 52, marginBottom: "0.75rem", display: "block" },
  title: { fontSize: "1.75rem", fontWeight: 700, margin: 0, color: "#f8fafc" },
  subtitle: { color: "#94a3b8", marginTop: "0.5rem" },
  section: { marginBottom: "1.5rem" },
  label: { display: "block", marginBottom: "0.5rem", fontWeight: 500 },
  textarea: {
    width: "100%",
    padding: "0.75rem",
    borderRadius: 8,
    border: "1px solid #334155",
    background: "#1e293b",
    color: "#f1f5f9",
    fontSize: "1rem",
    resize: "vertical",
    boxSizing: "border-box",
  },
  primaryBtn: {
    marginTop: "0.75rem",
    padding: "0.6rem 1.25rem",
    borderRadius: 8,
    border: "none",
    background: "#3b82f6",
    color: "#fff",
    fontWeight: 600,
    cursor: "pointer",
  },
  runAllBtn: {
    display: "block",
    width: "100%",
    marginTop: "0.75rem",
    padding: "0.7rem 1.25rem",
    borderRadius: 8,
    border: "none",
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    color: "#fff",
    fontWeight: 700,
    fontSize: "1.05rem",
    cursor: "pointer",
  },
  retryBtn: {
    display: "block",
    width: "100%",
    marginTop: "0.5rem",
    padding: "0.5rem 1rem",
    borderRadius: 8,
    border: "1px solid #f59e0b",
    background: "#451a03",
    color: "#fbbf24",
    fontWeight: 600,
    cursor: "pointer",
  },
  pipelineProgress: {
    display: "flex",
    gap: "1rem",
    marginTop: "0.75rem",
    padding: "0.6rem 0.75rem",
    borderRadius: 8,
    background: "#1e293b",
    border: "1px solid #334155",
    justifyContent: "space-around",
  },
  pipelineItem: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    gap: "0.25rem",
  },
  pipelineIcon: { fontSize: "1.25rem" },
  pipelineLabel: { fontSize: "0.7rem", color: "#94a3b8", textAlign: "center" as const },
  agentRow: { display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.75rem" },
  agentBtn: {
    padding: "0.5rem 1rem",
    borderRadius: 8,
    border: "1px solid #475569",
    background: "#1e293b",
    color: "#e2e8f0",
    cursor: "pointer",
  },
  exportRow: {
    display: "flex",
    gap: "0.5rem",
    marginTop: "0.75rem",
    alignItems: "center",
  },
  formatSelect: {
    flex: 1,
    padding: "0.5rem 0.75rem",
    borderRadius: 8,
    border: "1px solid #475569",
    background: "#1e293b",
    color: "#e2e8f0",
    fontSize: "0.9rem",
    cursor: "pointer",
  },
  downloadBtn: {
    padding: "0.5rem 1.25rem",
    borderRadius: 8,
    border: "none",
    background: "#059669",
    color: "#fff",
    fontWeight: 600,
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
  },
  meta: { color: "#94a3b8", fontSize: "0.875rem" },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "0.75rem",
  },
  sectionTitle: { fontSize: "1.125rem", margin: 0 },
  toggleJsonBtn: {
    padding: "0.3rem 0.6rem",
    borderRadius: 6,
    border: "1px solid #475569",
    background: "transparent",
    color: "#94a3b8",
    fontSize: "0.75rem",
    cursor: "pointer",
  },
  artifactCard: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 8,
    padding: "1rem",
    marginBottom: "0.75rem",
  },
  artifactTitle: {
    fontSize: "0.85rem",
    color: "#94a3b8",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
    marginBottom: "0.75rem",
    paddingBottom: "0.4rem",
    borderBottom: "1px solid #334155",
  },
  json: {
    background: "#1e293b",
    padding: "1rem",
    borderRadius: 8,
    overflow: "auto",
    fontSize: "0.8rem",
    border: "1px solid #334155",
    maxHeight: 480,
  },
  error: { color: "#f87171", background: "#450a0a", padding: "0.75rem", borderRadius: 8 },
  success: { color: "#4ade80", fontSize: "0.875rem" },
};
