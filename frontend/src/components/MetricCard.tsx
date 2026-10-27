import React from "react";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subValue?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  accentColor?: "cyan" | "green" | "red" | "purple" | "amber";
  badge?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subValue,
  icon: Icon,
  trend,
  accentColor = "cyan",
  badge,
}) => {
  const getAccentBorder = () => {
    switch (accentColor) {
      case "green":
        return "rgba(16, 185, 129, 0.4)";
      case "red":
        return "rgba(239, 68, 68, 0.4)";
      case "purple":
        return "rgba(139, 92, 246, 0.4)";
      case "amber":
        return "rgba(245, 158, 11, 0.4)";
      default:
        return "rgba(56, 189, 248, 0.4)";
    }
  };

  const getIconColor = () => {
    switch (accentColor) {
      case "green":
        return "#10b981";
      case "red":
        return "#ef4444";
      case "purple":
        return "#a855f7";
      case "amber":
        return "#f59e0b";
      default:
        return "#38bdf8";
    }
  };

  return (
    <div
      className="glass-panel"
      style={{
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        borderTop: `2px solid ${getAccentBorder()}`,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
        <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", fontWeight: 500 }}>
          {title}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          {badge}
          {Icon && (
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.03)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: getIconColor(),
              }}
            >
              <Icon size={18} />
            </div>
          )}
        </div>
      </div>

      <div>
        <div
          className="tabular-nums"
          style={{
            fontSize: "1.5rem",
            fontWeight: 700,
            color:
              trend === "up"
                ? "var(--color-bullish)"
                : trend === "down"
                ? "var(--color-bearish)"
                : "var(--text-highlight)",
            letterSpacing: "-0.02em",
          }}
        >
          {value}
        </div>
        {subValue && (
          <div
            style={{
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              marginTop: "0.25rem",
            }}
          >
            {subValue}
          </div>
        )}
      </div>
    </div>
  );
};
