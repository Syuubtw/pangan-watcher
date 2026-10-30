// components/ui/StatCard.tsx
interface StatCardProps {
  label: string;
  value: string | number;
  icon: string;
  color?: "blue" | "green" | "yellow" | "red" | "purple";
  sub?: string;
}

const colorStyles = {
  blue: {
    border: "rgba(59, 130, 246, 0.3)",
    borderHover: "rgba(59, 130, 246, 0.6)",
    bg: "rgba(59, 130, 246, 0.08)",
    badgeBg: "rgba(59, 130, 246, 0.15)",
    textColor: "#60a5fa",
    glow: "rgba(59, 130, 246, 0.15)",
  },
  green: {
    border: "rgba(34, 197, 94, 0.3)",
    borderHover: "rgba(34, 197, 94, 0.6)",
    bg: "rgba(34, 197, 94, 0.08)",
    badgeBg: "rgba(34, 197, 94, 0.15)",
    textColor: "#4ade80",
    glow: "rgba(34, 197, 94, 0.15)",
  },
  yellow: {
    border: "rgba(245, 158, 11, 0.3)",
    borderHover: "rgba(245, 158, 11, 0.6)",
    bg: "rgba(245, 158, 11, 0.08)",
    badgeBg: "rgba(245, 158, 11, 0.15)",
    textColor: "#fbbf24",
    glow: "rgba(245, 158, 11, 0.15)",
  },
  red: {
    border: "rgba(239, 68, 68, 0.3)",
    borderHover: "rgba(239, 68, 68, 0.6)",
    bg: "rgba(239, 68, 68, 0.08)",
    badgeBg: "rgba(239, 68, 68, 0.15)",
    textColor: "#f87171",
    glow: "rgba(239, 68, 68, 0.15)",
  },
  purple: {
    border: "rgba(168, 85, 247, 0.3)",
    borderHover: "rgba(168, 85, 247, 0.6)",
    bg: "rgba(168, 85, 247, 0.08)",
    badgeBg: "rgba(168, 85, 247, 0.15)",
    textColor: "#c084fc",
    glow: "rgba(168, 85, 247, 0.15)",
  },
};

export default function StatCard({ label, value, icon, color = "blue", sub }: StatCardProps) {
  const c = colorStyles[color] || colorStyles.blue;
  return (
    <div
      style={{
        background: "linear-gradient(180deg, #131c31 0%, #0e1628 100%)",
        borderRadius: 16,
        border: `1px solid ${c.border}`,
        padding: "20px 22px",
        boxShadow: `0 4px 20px ${c.glow}`,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        transition: "all 0.2s ease",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div>
          <div style={{ fontSize: 11, color: "#8899bb", fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>
            {label}
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#f0f6ff", letterSpacing: -0.5, lineHeight: 1.1 }}>
            {value}
          </div>
        </div>
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: c.badgeBg,
            border: `1px solid ${c.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 20,
            flexShrink: 0,
          }}
        >
          {icon}
        </div>
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: "#7182a3", marginTop: 12, paddingTop: 10, borderTop: "1px solid rgba(255,255,255,0.04)" }}>
          {sub}
        </div>
      )}
    </div>
  );
}
