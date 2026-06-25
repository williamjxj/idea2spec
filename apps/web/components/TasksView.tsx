"use client";

import type { Tasks } from "@/lib/api";

const s: Record<string, React.CSSProperties> = {
  section: { marginBottom: "1.25rem" },
  heading: { fontSize: "1.1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" },
  card: { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "0.5rem 0.75rem", marginBottom: "0.4rem" },
  epicBadge: { background: "#312e81", color: "#a5b4fc", fontSize: "0.7rem", fontWeight: 600, borderRadius: 4, padding: "0.1rem 0.4rem", marginRight: "0.5rem" },
  listItem: { color: "#e2e8f0", fontSize: "0.9rem", padding: "0.35rem 0", borderBottom: "1px solid #1e293b", display: "flex", alignItems: "flex-start", gap: "0.5rem" },
  issueNum: { color: "#64748b", fontSize: "0.8rem", minWidth: "1.5rem", flexShrink: 0 },
  list: { listStyle: "none", padding: 0, margin: 0 },
  icon: { fontSize: "1.1rem" },
};

export default function TasksView({ data }: { data: Tasks }) {
  return (
    <div>
      <div style={s.section}>
        <div style={s.heading}><span style={s.icon}>📋</span> Epics</div>
        {data.epics.length === 0 ? (
          <div style={s.card}><span style={{ color: "#64748b" }}>No epics defined</span></div>
        ) : (
          <ul style={s.list}>
            {data.epics.map((e, i) => (
              <li key={i} style={s.listItem}>
                <span style={s.epicBadge}>EPIC-{i + 1}</span>
                <span>{e}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div style={s.section}>
        <div style={s.heading}><span style={s.icon}>✅</span> Issues</div>
        {data.issues.length === 0 ? (
          <div style={s.card}><span style={{ color: "#64748b" }}>No issues defined</span></div>
        ) : (
          <ul style={s.list}>
            {data.issues.map((issue, i) => (
              <li key={i} style={s.listItem}>
                <span style={s.issueNum}>#{i + 1}</span>
                <span>{issue}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
