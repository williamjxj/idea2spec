"use client";

import type { BusinessAnalysis } from "@/lib/api";

const s: Record<string, React.CSSProperties> = {
  section: { marginBottom: "1.25rem" },
  heading: { fontSize: "1.1rem", fontWeight: 600, color: "#f8fafc", marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" },
  card: { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "0.75rem 1rem", marginBottom: "0.75rem" },
  label: { fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.3rem" },
  text: { color: "#e2e8f0", lineHeight: 1.6, fontSize: "0.9rem" },
  badgeRow: { display: "flex", flexWrap: "wrap", gap: "0.4rem" },
  badge: { background: "#0f172a", border: "1px solid #475569", borderRadius: 4, padding: "0.2rem 0.55rem", fontSize: "0.8rem", color: "#94a3b8" },
  highlight: { borderLeft: "3px solid #10b981", paddingLeft: "0.75rem", background: "#0f172a", borderRadius: 4, padding: "0.6rem 0.75rem" },
  icon: { fontSize: "1.1rem" },
};

export default function BusinessView({ data }: { data: BusinessAnalysis }) {
  return (
    <div>
      <div style={s.section}>
        <div style={s.heading}><span style={s.icon}>📊</span> Market Analysis</div>
        <div style={s.card}>
          <p style={s.text}>{data.market || "No market analysis available."}</p>
        </div>
      </div>
      <div style={s.section}>
        <div style={s.heading}><span style={s.icon}>🏆</span> Competitors</div>
        <div style={s.badgeRow}>
          {data.competitors.length === 0 && <span style={{ ...s.text, color: "#64748b" }}>None listed</span>}
          {data.competitors.map((c, i) => (
            <span key={i} style={s.badge}>{c}</span>
          ))}
        </div>
      </div>
      <div style={s.section}>
        <div style={s.heading}><span style={s.icon}>💰</span> Monetization</div>
        <div style={s.highlight}>
          <p style={s.text}>{data.monetization || "No monetization strategy available."}</p>
        </div>
      </div>
    </div>
  );
}
