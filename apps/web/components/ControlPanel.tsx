"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  createProject,
  deleteProject,
  formatApiError,
  getExportZipUrl,
  getProject,
  listProjects,
  runAgent,
  runAllAgents,
  saveProjectArtifacts,
  type AgentKey,
  type PipelineState,
  type PipelineStatus,
  type Project,
  type SaveArtifactsPayload,
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

/** Which LLM drives each agent — shown on buttons for transparency. */
const AGENT_LLM_INFO: Record<string, { provider: string; model: string; icon: string }> = {
  business: { provider: "Kimi", model: "kimi-k2.5", icon: "\uD83D\uDD2E" },
  product: { provider: "DeepSeek", model: "deepseek-v4-pro", icon: "\uD83E\uDDE0" },
  architect: { provider: "DeepSeek", model: "deepseek-v4-pro", icon: "\uD83C\uDFD7\uFE0F" },
  planner: { provider: "MiniMax", model: "MiniMax-M2.5", icon: "\uD83D\uDCCB" },
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
  const [savedToDb, setSavedToDb] = useState(false);
  const [exportPath, setExportPath] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedProjects, setSavedProjects] = useState<Project[]>([]);
  const [showSavedProjects, setShowSavedProjects] = useState(false);
  const [loadingSaved, setLoadingSaved] = useState(false);
  const [editableJson, setEditableJson] = useState("");
  const [editMode, setEditMode] = useState(false);
  const projectRef = useRef(project);
  projectRef.current = project;
  const [agentElapsed, setAgentElapsed] = useState<Record<string, string>>({});
  const agentStartRef = useRef<Record<string, number>>({});

  // 1-second tick for elapsed times on running agents
  useEffect(() => {
    const hasRunning = Object.values(agentStatus).includes("running");
    if (!hasRunning) return;
    const interval = setInterval(() => {
      const next: Record<string, string> = {};
      for (const [agent, status] of Object.entries(agentStatus)) {
        if (status === "running") {
          const start = agentStartRef.current[agent];
          if (start) {
            const sec = Math.floor((Date.now() - start) / 1000);
            next[agent] = sec >= 60 ? `${Math.floor(sec / 60)}m${sec % 60}s` : `${sec}s`;
          }
        }
      }
      setAgentElapsed(next);
    }, 1000);
    return () => clearInterval(interval);
  }, [agentStatus]);

  const isBusy = loading !== null || pipelineRunning || saving;

  // Fetch saved projects list
  const fetchSavedProjects = useCallback(async () => {
    setLoadingSaved(true);
    try {
      const projects = await listProjects();
      setSavedProjects(projects);
    } catch {
      // silently fail
    } finally {
      setLoadingSaved(false);
    }
  }, []);

  // Load a saved project from DB for viewing
  const handleLoadProject = useCallback(async (projectId: string) => {
    try {
      const p = await getProject(projectId);
      setProject(p);
      setPipelineState("idle");
      setAgentStatus(initialPipelineStatus());
      setSavedToDb(true);
      setExportPath(null);
      setError(null);
      setEditMode(false);
    } catch (e) {
      setError(formatApiError(e));
    }
  }, []);

  // Delete a saved project
  const handleDeleteProject = useCallback(async (projectId: string) => {
    try {
      await deleteProject(projectId);
      await fetchSavedProjects();
    } catch (e) {
      setError(formatApiError(e));
    }
  }, [fetchSavedProjects]);

  const handleRunAll = useCallback(() => {
    if (!project) return;
    setError(null);
    setSavedToDb(false);
    setPipelineRunning(true);
    setPipelineState("running");
    setAgentStatus(initialPipelineStatus());
    // Record start times for all agents
    const now = Date.now();
    for (const a of AGENT_ORDER) agentStartRef.current[a] = now;

    runAllAgents(project.id, {
      onAgentStart(agent) {
        setAgentStatus((prev) => ({ ...prev, [agent]: "running" }));
        agentStartRef.current[agent] = Date.now();
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
    setSavedToDb(false);
    setExportPath(null);
    try {
      const p = await createProject(idea.trim());
      setProject(p);
      setEditMode(false);
      await fetchSavedProjects();
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
    setSavedToDb(false);
    setAgentStatus((prev) => ({ ...prev, [agent]: "running" }));
    agentStartRef.current[agent] = Date.now();
    try {
      const p = await runAgent(project.id, agent);
      setProject(p);
      setAgentStatus((prev) => ({ ...prev, [agent]: "complete" }));
    } catch (e) {
      setAgentStatus((prev) => ({ ...prev, [agent]: "error" }));
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

  async function handleSaveToDb() {
    if (!project) return;
    setSaving(true);
    setError(null);
    try {
      let payload: SaveArtifactsPayload;
      if (editMode) {
        // Parse the edited JSON
        try {
          const parsed = JSON.parse(editableJson);
          payload = {
            business_analysis: parsed.business_analysis ?? null,
            prd: parsed.prd ?? null,
            architecture: parsed.architecture ?? null,
            tasks: parsed.tasks ?? null,
          };
        } catch {
          setError("Invalid JSON — fix errors before saving");
          setSaving(false);
          return;
        }
      } else {
        payload = {
          business_analysis: project.business_analysis ?? null,
          prd: project.prd ?? null,
          architecture: project.architecture ?? null,
          tasks: project.tasks ?? null,
        };
      }
      const saved = await saveProjectArtifacts(project.id, payload);
      setProject(saved.project);
      setSavedToDb(true);
      setEditMode(false);
      setExportPath(saved.export_path);
      await fetchSavedProjects();
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setSaving(false);
    }
  }

  // Enter edit mode with current JSON
  function handleEditJson() {
    if (!project) return;
    setEditableJson(JSON.stringify(
      { business_analysis: project.business_analysis ?? null, prd: project.prd ?? null, architecture: project.architecture ?? null, tasks: project.tasks ?? null },
      null,
      2
    ));
    setEditMode(true);
    setShowRawJson(true);
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

  const hasArtifacts = project?.business_analysis || project?.prd || project?.architecture || project?.tasks;

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <img src="/logo.svg" alt="AI Project CTO" style={styles.logo} />
        <p style={styles.subtitle}>
          Multi-agent workflow — transform an idea into structured project artifacts
        </p>
      </header>

      {/* ── Saved Projects Panel ── */}
      <section style={styles.section}>
        <button
          style={styles.savedProjectsToggle}
          onClick={() => { setShowSavedProjects(!showSavedProjects); if (!showSavedProjects) fetchSavedProjects(); }}
        >
          {showSavedProjects ? "\u25BC" : "\u25B6"} Saved Projects ({savedProjects.length})
        </button>
        {showSavedProjects && (
          <div style={styles.savedProjectsPanel}>
            {loadingSaved ? (
              <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>Loading...</p>
            ) : savedProjects.length === 0 ? (
              <p style={{ color: "#64748b", fontSize: "0.85rem" }}>No saved projects yet.</p>
            ) : (
              savedProjects.map((sp) => (
                <div key={sp.id} style={styles.savedProjectItem}>
                  <div style={{ flex: 1, overflow: "hidden" }}>
                    <span style={styles.savedProjectTitle}>{sp.title || sp.idea}</span>
                    <span style={styles.savedProjectMeta}>
                      {sp.created_at ? new Date(sp.created_at).toLocaleDateString() : ""}
                      {sp.business_analysis ? " \u2022 agent output saved" : " \u2022 idea only"}
                    </span>
                  </div>
                  <div style={styles.savedProjectActions}>
                    <button style={styles.loadBtn} onClick={() => handleLoadProject(sp.id)}>Load</button>
                    <button style={styles.delBtn} onClick={() => handleDeleteProject(sp.id)}>Delete</button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </section>

      {/* ── Create Project ── */}
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

      {/* ── Agent Controls ── */}
      {project && (
        <section style={styles.section}>
          <p style={styles.meta}>
            Project: <strong>{project.title || project.idea}</strong>
            &nbsp;|&nbsp;ID: <code>{project.id.slice(0, 8)}</code>
            {savedToDb && <span style={styles.savedBadge}> ✓ Saved</span>}
          </p>

          {/* ── Run All Button ── */}
          <button
            style={styles.runAllBtn}
            onClick={handleRunAll}
            disabled={isBusy}
          >
            {pipelineState === "running" ? "\uD83D\uDD04 Running All\u2026" : "Run All Agents (sequential)"}
          </button>

          {/* ── Per-Agent Status Rows (always visible) ── */}
          {AGENT_ORDER.map((key) => {
            const status = agentStatus[key];
            const llm = AGENT_LLM_INFO[key];
            const elapsed = agentElapsed[key];
            return (
              <div key={key} style={styles.agentStatusRow}>
                <span style={styles.agentStatusIcon}>
                  {status === "running" ? "\uD83D\uDD04" : AGENT_ICON[status]}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={styles.agentStatusLabel}>
                    {AGENTS.find((a) => a.key === key)?.label}
                    {status === "running" && elapsed && (
                      <span style={styles.elapsedBadge}>{elapsed}</span>
                    )}
                    {status === "complete" && <span style={styles.completeBadge}>Done</span>}
                    {status === "error" && <span style={styles.statusErrorBadge}>Failed</span>}
                    {(status === "pending" || status === undefined) && <span style={styles.pendingBadge}>Pending</span>}
                  </div>
                  <div style={styles.agentStatusLlm}>
                    {llm.icon} {llm.provider} &middot; {llm.model}
                  </div>
                </div>
              </div>
            );
          })}

          {pipelineState === "partial_failure" && (
            <button
              style={styles.retryBtn}
              onClick={handleRetryFromFailed}
              disabled={isBusy}
            >
              {pipelineRunning ? "Retrying\u2026" : `Retry from Failed (${getCompletedCount()}/4 done)`}
            </button>
          )}

          {/* ── Individual Agent Buttons ── */}
          <div style={styles.agentRow}>
            {AGENTS.map(({ key, label }) => {
              const llm = AGENT_LLM_INFO[key];
              return (
                <button
                  key={key}
                  style={styles.agentBtn}
                  onClick={() => handleRunAgent(key)}
                  disabled={isBusy}
                  title={`Uses ${llm.provider} (${llm.model})`}
                >
                  {loading === key ? (
                    <span>{"\uD83D\uDD04"} {agentElapsed[key] || "Running\u2026"}</span>
                  ) : (
                    <span>{llm.icon} {label}</span>
                  )}
                </button>
              );
            })}
          </div>
          <p style={styles.agentHint}>
            Run individually to execute one agent at a time, or <strong>Run All</strong> above to
            run all 4 agents sequentially (Business &rarr; Product &rarr; Architect &rarr; Planner).
            Re-running an agent replaces its previous output.
          </p>

          {/* ── Preview / Approve Flow ── */}
          {hasArtifacts && !savedToDb && (
            <div style={styles.approveBar}>
              <span style={{ fontSize: "0.85rem", color: "#fbbf24" }}>
                ⚠ Preview mode — artifacts not yet saved to database
              </span>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                <button
                  style={styles.saveBtn}
                  onClick={handleSaveToDb}
                  disabled={saving}
                >
                  {saving ? "Saving…" : "✓ Approve & Save to Database"}
                </button>
                <button
                  style={styles.editBtn}
                  onClick={handleEditJson}
                  disabled={editMode}
                >
                  {"\u270F"} Edit Artifacts (JSON)
                </button>
              </div>
            </div>
          )}

          {/* ── Saved confirmation ── */}
          {savedToDb && (
            <div style={styles.savedBar}>
              <div>✓ Artifacts saved to database</div>
              {exportPath && (
                <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.25rem" }}>
                  Filesystem: <code>{exportPath}</code>
                </div>
              )}
            </div>
          )}

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

      {/* ── Project Artifacts ── */}
      {project && (
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>Project Artifacts</h2>
            <button
              style={styles.toggleJsonBtn}
              onClick={() => { setShowRawJson(!showRawJson); if (editMode) setEditMode(false); }}
            >
              {showRawJson ? "Structured View" : "Raw JSON"}
            </button>
          </div>

          {/* Structured views */}
          {!showRawJson && project.business_analysis && (
            <div style={styles.artifactCard}>
              <h3 style={styles.artifactTitle}>Business Analysis</h3>
              <BusinessView data={project.business_analysis} />
            </div>
          )}
          {!showRawJson && project.prd && (
            <div style={styles.artifactCard}>
              <h3 style={styles.artifactTitle}>Product Requirements (PRD)</h3>
              <PRDView data={project.prd} />
            </div>
          )}
          {!showRawJson && project.architecture && (
            <div style={styles.artifactCard}>
              <h3 style={styles.artifactTitle}>Architecture</h3>
              <ArchitectureView data={project.architecture} />
            </div>
          )}
          {!showRawJson && project.tasks && (
            <div style={styles.artifactCard}>
              <h3 style={styles.artifactTitle}>Implementation Tasks</h3>
              <TasksView data={project.tasks} />
            </div>
          )}

          {/* Editable JSON (when in edit mode) */}
          {editMode && (
            <div>
              <p style={{ color: "#fbbf24", fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                Edit the JSON below, then click &quot;Approve &amp; Save to Database&quot; to persist.
              </p>
              <textarea
                style={{ ...styles.json, minHeight: 300, resize: "vertical" } as React.CSSProperties}
                value={editableJson}
                onChange={(e) => setEditableJson(e.target.value)}
              />
            </div>
          )}

          {/* Read-only JSON (show raw mode, not edit mode) */}
          {showRawJson && !editMode && (
            <pre style={styles.json}>{JSON.stringify(project, null, 2)}</pre>
          )}

          {/* Empty state */}
          {!hasArtifacts && !showRawJson && !editMode && (
            <p style={{ color: "#64748b", fontSize: "0.9rem" }}>
              Run agents to generate project artifacts. After reviewing, click &quot;Approve &amp; Save to Database&quot; to persist.
            </p>
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
  agentStatusRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.6rem",
    marginTop: "0.5rem",
    padding: "0.5rem 0.75rem",
    borderRadius: 8,
    background: "#1e293b",
    border: "1px solid #334155",
  },
  agentStatusIcon: { fontSize: "1.1rem", width: 24, textAlign: "center" as const },
  agentStatusLabel: {
    fontSize: "0.85rem",
    color: "#e2e8f0",
    fontWeight: 600,
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
  },
  agentStatusLlm: {
    fontSize: "0.7rem",
    color: "#64748b",
    marginTop: "0.15rem",
  },
  elapsedBadge: {
    fontSize: "0.7rem",
    padding: "0.1rem 0.4rem",
    borderRadius: 4,
    background: "#1e3a5f",
    color: "#60a5fa",
    fontWeight: 500,
  },
  completeBadge: {
    fontSize: "0.65rem",
    padding: "0.1rem 0.4rem",
    borderRadius: 4,
    background: "#064e3b",
    color: "#34d399",
    fontWeight: 600,
  },
  statusErrorBadge: {
    fontSize: "0.65rem",
    padding: "0.1rem 0.4rem",
    borderRadius: 4,
    background: "#450a0a",
    color: "#f87171",
    fontWeight: 600,
  },
  pendingBadge: {
    fontSize: "0.65rem",
    padding: "0.1rem 0.4rem",
    borderRadius: 4,
    background: "#1e293b",
    color: "#64748b",
    fontWeight: 500,
    border: "1px solid #334155",
  },
  agentRow: { display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.75rem" },
  agentBtn: {
    padding: "0.5rem 1rem",
    borderRadius: 8,
    border: "1px solid #475569",
    background: "#1e293b",
    color: "#e2e8f0",
    cursor: "pointer",
  },
  agentHint: {
    marginTop: "0.5rem",
    fontSize: "0.72rem",
    color: "#64748b",
    lineHeight: 1.4,
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
  savedProjectsToggle: {
    display: "block",
    width: "100%",
    padding: "0.5rem 0.75rem",
    borderRadius: 8,
    border: "1px solid #334155",
    background: "#1e293b",
    color: "#94a3b8",
    fontSize: "0.85rem",
    fontWeight: 600,
    cursor: "pointer",
    textAlign: "left" as const,
  },
  savedProjectsPanel: {
    marginTop: "0.5rem",
    padding: "0.75rem",
    borderRadius: 8,
    background: "#1e293b",
    border: "1px solid #334155",
    maxHeight: 240,
    overflowY: "auto" as const,
  },
  savedProjectItem: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.5rem 0.4rem",
    borderBottom: "1px solid #1e293b",
    fontSize: "0.8rem",
  },
  savedProjectTitle: {
    color: "#e2e8f0",
    display: "block",
    whiteSpace: "nowrap" as const,
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  savedProjectMeta: {
    color: "#64748b",
    fontSize: "0.7rem",
    display: "block",
  },
  savedProjectActions: {
    display: "flex",
    gap: "0.3rem",
    flexShrink: 0,
  },
  loadBtn: {
    padding: "0.2rem 0.5rem",
    borderRadius: 4,
    border: "1px solid #3b82f6",
    background: "transparent",
    color: "#60a5fa",
    fontSize: "0.7rem",
    cursor: "pointer",
  },
  delBtn: {
    padding: "0.2rem 0.5rem",
    borderRadius: 4,
    border: "1px solid #ef4444",
    background: "transparent",
    color: "#f87171",
    fontSize: "0.7rem",
    cursor: "pointer",
  },
  approveBar: {
    marginTop: "0.75rem",
    padding: "0.75rem",
    borderRadius: 8,
    background: "#422006",
    border: "1px solid #a16207",
  },
  saveBtn: {
    padding: "0.5rem 1rem",
    borderRadius: 8,
    border: "none",
    background: "linear-gradient(135deg, #059669, #10b981)",
    color: "#fff",
    fontWeight: 700,
    fontSize: "0.85rem",
    cursor: "pointer",
  },
  editBtn: {
    padding: "0.5rem 1rem",
    borderRadius: 8,
    border: "1px solid #a16207",
    background: "transparent",
    color: "#fbbf24",
    fontWeight: 600,
    fontSize: "0.85rem",
    cursor: "pointer",
  },
  savedBar: {
    marginTop: "0.75rem",
    padding: "0.5rem 0.75rem",
    borderRadius: 8,
    background: "#064e3b",
    border: "1px solid #059669",
    color: "#6ee7b7",
    fontSize: "0.85rem",
    fontWeight: 600,
  },
  savedBadge: { color: "#34d399", fontSize: "0.8rem", fontWeight: 600 },
};
