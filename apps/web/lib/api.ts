export type BusinessAnalysis = {
  market: string;
  competitors: string[];
  monetization: string;
};

export type PRD = {
  features: string[];
  user_stories: string[];
  roadmap: string[];
};

export type Architecture = {
  frontend: string;
  backend: string;
  database: string;
  infra: string;
};

export type Tasks = {
  epics: string[];
  issues: string[];
};

export type Project = {
  id: string;
  idea: string;
  title: string;
  business_analysis?: BusinessAnalysis | null;
  prd?: PRD | null;
  architecture?: Architecture | null;
  tasks?: Tasks | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type SaveArtifactsPayload = {
  business_analysis?: BusinessAnalysis | null;
  prd?: PRD | null;
  architecture?: Architecture | null;
  tasks?: Tasks | null;
};

/** Same-origin proxy via Next.js rewrites (/api → FastAPI). Override for direct calls. */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export type AgentKey = "business" | "product" | "architect" | "planner";

export type PipelineStatus = Record<AgentKey, "pending" | "running" | "complete" | "error">;

export type PipelineState = "idle" | "running" | "complete" | "partial_failure";

/** Try to parse a backend error response body for a clean `detail` message. */
function _parseErrorBody(text: string): string {
  try {
    const parsed = JSON.parse(text);
    if (typeof parsed.detail === "string") return parsed.detail;
    if (typeof parsed.detail === "object" && parsed.detail?.msg) return parsed.detail.msg;
  } catch {
    // not JSON — use raw text
  }
  // Truncate very long error bodies
  return text.length > 300 ? text.slice(0, 300) + "..." : text;
}

export function formatApiError(error: unknown): string {
  if (error instanceof TypeError) {
    return (
      "Cannot reach the API. Start the backend with `make api` (port 8100), " +
      "ensure `apps/web/.env.local` has BACKEND_URL if not using defaults, then restart `make web`."
    );
  }
  if (error instanceof Error) {
    return _parseErrorBody(error.message);
  }
  return "Request failed";
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch (error) {
    throw new TypeError(formatApiError(error));
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function createProject(idea: string): Promise<Project> {
  return api<Project>("/project/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea }),
  });
}

export async function runAgent(
  projectId: string,
  agent: "business" | "product" | "architect" | "planner"
): Promise<Project> {
  return api<Project>(`/agent/${agent}/${projectId}`, { method: "POST" });
}

export async function exportProject(
  projectId: string
): Promise<{ path: string; project: Project }> {
  return api<{ path: string; project: Project }>(
    `/project/${projectId}/export`,
    { method: "POST" }
  );
}

export function getExportZipUrl(projectId: string, format: "markdown" | "html" | "mermaid" = "markdown"): string {
  return `${API_BASE}/project/${projectId}/export/zip?format=${format}`;
}

export async function getProject(projectId: string): Promise<Project> {
  return api<Project>(`/project/${projectId}`);
}

export async function saveProjectArtifacts(
  projectId: string,
  payload: SaveArtifactsPayload
): Promise<{ project: Project; export_path: string }> {
  return api<{ project: Project; export_path: string }>(`/project/${projectId}/save-artifacts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listProjects(): Promise<Project[]> {
  return api<Project[]>("/projects");
}

export async function deleteProject(projectId: string): Promise<{ deleted: string; idea: string }> {
  return api<{ deleted: string; idea: string }>(`/project/${projectId}`, { method: "DELETE" });
}

export type SSEHandler = {
  onAgentStart?: (agent: AgentKey) => void;
  onAgentComplete?: (agent: AgentKey) => void;
  onAgentError?: (agent: AgentKey, error: string) => void;
  onComplete?: (project: Project) => void;
  onError?: (error: string) => void;
};

/**
 * Quick health check via the same-origin Next.js proxy.
 */
async function _checkBackendHealth(): Promise<string | null> {
  try {
    const resp = await fetch("/api/health", { method: "GET" });
    if (!resp.ok) return `Backend health check returned status ${resp.status}${resp.status === 404 ? " — proxy may not be configured correctly" : ""}`;
    return null;
  } catch (err) {
    const msg = err instanceof TypeError ? err.message : String(err);
    return `Cannot reach the API: ${msg}. Ensure the backend is running (\`make api\`).`;
  }
}

/** Run all 4 agents sequentially, calling per-agent status handlers in real time.
 *
 * Each agent runs via `POST /api/agent/{name}/{id}` — same endpoint used by
 * individual agent buttons.  Results are accumulated on the frontend, so
 * `onComplete` receives a single Project with all 4 artifact fields set.
 *
 * If any agent fails the pipeline stops and `onAgentError` is called.
 * The optional AbortSignal allows the caller to cancel mid-pipeline.
 */
const ALL_AGENTS: AgentKey[] = ["business", "product", "architect", "planner"];

const AGENT_CALL_TIMEOUT_MS = 180_000;

export async function runAllAgents(
  projectId: string,
  handlers: SSEHandler,
  signal?: AbortSignal,
): Promise<void> {
  const healthError = await _checkBackendHealth();
  if (healthError) {
    handlers.onError?.(healthError);
    return;
  }

  let accumulated: Project | null = null;

  for (const agent of ALL_AGENTS) {
    if (signal?.aborted) {
      handlers.onError?.("Run All was cancelled.");
      return;
    }

    handlers.onAgentStart?.(agent);

    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), AGENT_CALL_TIMEOUT_MS);
      if (signal) signal.onabort = () => { ctrl.abort(); clearTimeout(timer); };

      const res = await fetch(`${API_BASE}/agent/${agent}/${projectId}`, {
        method: "POST",
        signal: ctrl.signal,
      });
      clearTimeout(timer);

      if (!res.ok) {
        const body = await res.text().catch(() => "");
        handlers.onAgentError?.(agent, `Server error (${res.status}): ${_parseErrorBody(body)}`);
        return;
      }

      const result: Project = await res.json();

      const prev = accumulated as Project | null;
      accumulated = prev
        ? {
            ...prev,
            business_analysis: result.business_analysis ?? prev.business_analysis,
            prd: result.prd ?? prev.prd,
            architecture: result.architecture ?? prev.architecture,
            tasks: result.tasks ?? prev.tasks,
          }
        : result;

      handlers.onAgentComplete?.(agent);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        handlers.onError?.("Run All was cancelled.");
        return;
      }
      const msg = err instanceof Error ? err.message : String(err);
      handlers.onAgentError?.(agent, msg);
      return;
    }
  }

  if (accumulated) {
    handlers.onComplete?.(accumulated);
  }
}
