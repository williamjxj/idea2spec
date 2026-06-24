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
  business_analysis?: BusinessAnalysis | null;
  prd?: PRD | null;
  architecture?: Architecture | null;
  tasks?: Tasks | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
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

export async function getProject(projectId: string): Promise<Project> {
  return api<Project>(`/project/${projectId}`);
}
