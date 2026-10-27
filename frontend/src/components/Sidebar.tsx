import React from "react";
import {
  LayoutDashboard,
  CandlestickChart,
  BrainCircuit,
  ListOrdered,
  ShieldAlert,
  BarChart3,
  Sliders,
  DollarSign,
  TrendingUp,
} from "lucide-react";
import { RiskStatus } from "../types";

export type NavPage =
  | "overview"
  | "terminal"
  | "analysis"
  | "positions"
  | "risk"
  | "reports"
  | "settings";

interface SidebarProps {
  currentPage: NavPage;
  onSelectPage: (page: NavPage) => void;
  riskStatus?: RiskStatus | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  riskStatus,
}) => {
  const navItems: Array<{ id: NavPage; label: string; icon: React.ReactNode; badge?: string }> = [
    {
      id: "overview",
      label: "Overview",
      icon: <LayoutDashboard size={18} />,
    },
    {
      id: "terminal",
      label: "Trading Terminal",
      icon: <CandlestickChart size={18} />,
    },
    {
      id: "analysis",
      label: "AI Strategy Intel",
      icon: <BrainCircuit size={18} />,
      badge: "ML",
    },
    {
      id: "positions",
      label: "Positions & Trades",
      icon: <ListOrdered size={18} />,
    },
    {
      id: "risk",
      label: "Risk & Controls",
      icon: <ShieldAlert size={18} />,
      badge: riskStatus?.is_locked ? "LOCK" : undefined,
    },
    {
      id: "reports",
      label: "Reports & Analytics",
      icon: <BarChart3 size={18} />,
    },
    {
      id: "settings",
      label: "Settings & Health",
      icon: <Sliders size={18} />,
    },
  ];

  const balance = riskStatus?.account_balance ?? 0;
  const equity = riskStatus?.account_equity ?? 0;
  const dailyLossPct = riskStatus?.daily_loss_pct ?? 0;

  return (
    <aside className="sidebar">
      {/* Navigation links */}
      <nav style={{ padding: "1.25rem 0.75rem", flex: 1, display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        <div
          style={{
            fontSize: "0.7rem",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--text-muted)",
            padding: "0.25rem 0.75rem 0.5rem",
            fontWeight: 700,
          }}
        >
          Navigation
        </div>

        {navItems.map((item) => {
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectPage(item.id)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.65rem 0.85rem",
                borderRadius: "var(--radius-md)",
                border: "none",
                background: isActive ? "linear-gradient(90deg, rgba(56, 189, 248, 0.15) 0%, rgba(56, 189, 248, 0.03) 100%)" : "transparent",
                color: isActive ? "#38bdf8" : "var(--text-secondary)",
                cursor: "pointer",
                textAlign: "left",
                fontFamily: "var(--font-main)",
                fontSize: "0.875rem",
                fontWeight: isActive ? 600 : 500,
                borderLeft: isActive ? "3px solid #38bdf8" : "3px solid transparent",
                transition: "all 0.15s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                {item.icon}
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span
                  style={{
                    fontSize: "0.65rem",
                    fontWeight: 700,
                    padding: "0.15rem 0.45rem",
                    borderRadius: "4px",
                    background: item.badge === "LOCK" ? "rgba(239, 68, 68, 0.2)" : "rgba(139, 92, 246, 0.2)",
                    color: item.badge === "LOCK" ? "#f87171" : "#c084fc",
                  }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Account Balance Widget */}
      <div
        style={{
          padding: "1rem",
          margin: "0.75rem",
          background: "rgba(16, 24, 40, 0.6)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-md)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.6rem" }}>
          <DollarSign size={14} color="#38bdf8" />
          <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>
            Demo Account
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
            <span style={{ color: "var(--text-muted)" }}>Balance:</span>
            <span className="tabular-nums" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
              ${balance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
            <span style={{ color: "var(--text-muted)" }}>Equity:</span>
            <span className="tabular-nums" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
              ${equity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", borderTop: "1px solid var(--border-subtle)", paddingTop: "0.4rem" }}>
            <span style={{ color: "var(--text-muted)" }}>Daily Loss:</span>
            <span
              className="tabular-nums"
              style={{
                color: dailyLossPct > 0.8 ? "var(--color-bearish)" : "var(--text-secondary)",
                fontWeight: 600,
              }}
            >
              {dailyLossPct.toFixed(2)}% / {riskStatus?.max_daily_loss_pct ?? 1.0}%
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
