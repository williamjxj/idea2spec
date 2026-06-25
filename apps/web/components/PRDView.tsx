"use client";

import type { PRD } from "@/lib/api";

const s: Record<string, React.CSSProperties> = {
  section: { marginBottom: "1.25rem" },
  heading: { fontSize: "1.1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" },
  card: { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "0.5rem 0.75rem", marginBottom: "0.4rem" },
  list: { listStyle: "none", padding: 0, margin: 0 },
  listItem: { padding: "0.4rem 0", borderBottom: "1px solid #1e293b", color: "#e2e8f0", fontSize: "0.9rem", display: "flex", alignItems: "flex-start", gap: "0.5rem" },
  bullet: { color: "#3b82f6", flexShrink: 0 },
  timeline: { position: "relative", paddingLeft: "1.25rem" },
  timelineLine: { position: "absolute", left: "0.35rem", top: "0.5rem", bottom: "0.5rem", width: 2, background: "#334155" },
  timelineDot: { position: "absolute", left: "-0.65rem", top: "0.55rem", width: 10, height: 10, borderRadius: "50%", background: "#6366f1" },
  timelineItem: { position: "relative", marginBottom: "0.75rem", paddingLeft: "0.5rem" },
  icon: { fontSize: "1.1rem" },
};

export default function PRDView({ data }: { data: PRD }) {
  return (
    <div>
      <div style={s.section}>
        <div style={s.heading}><span style={s.icon}>✨</span> Features</div>
        {data.features.length === 0 ? (
          <div style={s.card}><span style={{ color: "#64748b" }}>No features listed</span></div>
        ) : (
          <ul style={s.list}>
            {data.features.map((f, i) => (
              <li key={i} style={s.listItem}>
                <span style={s.bullet}>▸</span>
                <span>{f}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div style={s.section}>
        <div style={s.heading}><span style={s.icon}>📖</span> User Stories</div>
        {data.user_stories.length === 0 ? (
          <div style={s.card}><span style={{ color: "#64748b" }}>No user stories listed</span></div>
        ) : (
          <ul style={s.list}>
            {data.user_stories.map((st, i) => (
              <li key={i} style={s.listItem}>
                <span style={s.bullet}>👤</span>
                <span>{st}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div style={s.section}>
        <div style={s.heading}><span style={s.icon}>🗺️</span> Roadmap</div>
        <div style={s.timeline}>
          <div style={s.timelineLine} />
          {data.roadmap.length === 0 ? (
            <div style={{ ...s.card, marginLeft: "0.5rem" }}><span style={{ color: "#64748b" }}>No roadmap defined</span></div>
          ) : (
            data.roadmap.map((r, i) => (
              <div key={i} style={s.timelineItem}>
                <div style={s.timelineDot} />
                <div style={s.card}>
                  <span style={{ color: "#94a3b8", fontSize: "0.75rem", fontWeight: 600 }}>Phase {i + 1}</span>
                  <p style={{ color: "#e2e8f0", fontSize: "0.9rem", margin: "0.2rem 0 0" }}>{r}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
