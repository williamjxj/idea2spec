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

export function formatApiError(error: unknown): string {
  if (error instanceof TypeError) {
    return (
      "Cannot reach the API. Start the backend with `make api` (port 8100), " +
      "ensure `apps/web/.env.local` has BACKEND_URL if not using defaults, then restart `make web`."
    );
  }
  if (error instanceof Error) {
    return error.message;
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

export async function runAllAgents(projectId: string, handlers: SSEHandler): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/project/${projectId}/run-all`, { method: "POST" });
  } catch {
    handlers.onError?.("Cannot reach the API server.");
    return;
  }
  if (!res.ok) {
    handlers.onError?.(`Server error: ${res.status}`);
    return;
  }
  if (!res.body) {
    handlers.onError?.("Response has no body stream.");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const lines = part.split("\n");
        let eventType = "";
        let dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) eventType = line.slice(7);
          if (line.startsWith("data: ")) dataStr = line.slice(6);
        }
        if (!eventType || !dataStr) continue;

        try {
          const data = JSON.parse(dataStr);
          switch (eventType) {
            case "agent_start":
              handlers.onAgentStart?.(data.agent);
              break;
            case "agent_complete":
              handlers.onAgentComplete?.(data.agent);
              break;
            case "agent_error":
              handlers.onAgentError?.(data.agent, data.error);
              return;
            case "complete":
              handlers.onComplete?.(data.project);
              return;
          }
        } catch {
          // skip malformed events
        }
      }
    }
  } catch (err) {
    handlers.onError?.(err instanceof Error ? err.message : "Stream read error");
  } finally {
    reader.releaseLock();
  }
}
