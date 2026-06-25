"use client";

import type { Architecture } from "@/lib/api";

const s: Record<string, React.CSSProperties> = {
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" },
  card: { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "0.75rem" },
  label: { fontSize: "0.72rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.3rem" },
  text: { color: "#e2e8f0", fontSize: "0.85rem", lineHeight: 1.5, margin: 0 },
  icon: { fontSize: "1.1rem" },
};

type ArchSection = { key: string; label: string; icon: string };

const SECTIONS: ArchSection[] = [
  { key: "frontend", label: "Frontend", icon: "🖥️" },
  { key: "backend", label: "Backend", icon: "⚙️" },
  { key: "database", label: "Database", icon: "🗄️" },
  { key: "infra", label: "Infrastructure", icon: "☁️" },
];

export default function ArchitectureView({ data }: { data: Architecture }) {
  return (
    <div>
      <div style={s.grid}>
        {SECTIONS.map((sec) => (
          <div key={sec.key} style={s.card}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.4rem" }}>
              <span style={s.icon}>{sec.icon}</span>
              <span style={s.label}>{sec.label}</span>
            </div>
            <p style={s.text}>
              {(data as Record<string, string>)[sec.key] || <span style={{ color: "#64748b" }}>Not specified</span>}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
