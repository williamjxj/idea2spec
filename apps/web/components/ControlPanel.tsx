"use client";

import { useState } from "react";
import {
  createProject,
  exportProject,
  runAgent,
  type Project,
} from "@/lib/api";

type AgentKey = "business" | "product" | "architect" | "planner";

const AGENTS: { key: AgentKey; label: string }[] = [
  { key: "business", label: "Business Analyst" },
  { key: "product", label: "Product Manager" },
  { key: "architect", label: "Architect" },
  { key: "planner", label: "Engineering Planner" },
];

export default function ControlPanel() {
  const [idea, setIdea] = useState("");
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState<AgentKey | "create" | "export" | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [exportPath, setExportPath] = useState<string | null>(null);

  async function handleCreate() {
    if (!idea.trim()) return;
    setLoading("create");
    setError(null);
    setExportPath(null);
    try {
      const p = await createProject(idea.trim());
      setProject(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create project");
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
      setError(e instanceof Error ? e.message : `Failed to run ${agent} agent`);
    } finally {
      setLoading(null);
    }
  }

  async function handleExport() {
    if (!project) return;
    setLoading("export");
    setError(null);
    try {
      const result = await exportProject(project.id);
      setProject(result.project);
      setExportPath(result.path);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to export");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>AI Project CTO</h1>
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
          disabled={loading !== null || !idea.trim()}
        >
          {loading === "create" ? "Creating…" : "Create Project"}
        </button>
      </section>

      {project && (
        <section style={styles.section}>
          <p style={styles.meta}>
            Project ID: <code>{project.id}</code>
          </p>
          <div style={styles.agentRow}>
            {AGENTS.map(({ key, label }) => (
              <button
                key={key}
                style={styles.agentBtn}
                onClick={() => handleRunAgent(key)}
                disabled={loading !== null}
              >
                {loading === key ? "Running…" : `Run ${label}`}
              </button>
            ))}
            <button
              style={styles.exportBtn}
              onClick={handleExport}
              disabled={loading !== null}
            >
              {loading === "export" ? "Exporting…" : "Export Workspace"}
            </button>
          </div>
          {exportPath && (
            <p style={styles.success}>Exported to: {exportPath}</p>
          )}
        </section>
      )}

      {error && <p style={styles.error}>{error}</p>}

      {project && (
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>Project State</h2>
          <pre style={styles.json}>{JSON.stringify(project, null, 2)}</pre>
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
  agentRow: { display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.75rem" },
  agentBtn: {
    padding: "0.5rem 1rem",
    borderRadius: 8,
    border: "1px solid #475569",
    background: "#1e293b",
    color: "#e2e8f0",
    cursor: "pointer",
  },
  exportBtn: {
    padding: "0.5rem 1rem",
    borderRadius: 8,
    border: "none",
    background: "#059669",
    color: "#fff",
    cursor: "pointer",
  },
  meta: { color: "#94a3b8", fontSize: "0.875rem" },
  sectionTitle: { fontSize: "1.125rem", marginBottom: "0.75rem" },
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
