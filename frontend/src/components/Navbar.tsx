import React, { useState, useEffect } from "react";
import { ShieldCheck, ShieldAlert, RefreshCw, Cpu, Activity, Clock } from "lucide-react";
import { BotState, HealthStatus, MT5StatusInfo, RiskStatus } from "../types";
import { StatusBadge } from "./StatusBadge";

interface NavbarProps {
  botState?: BotState | null;
  health?: HealthStatus | null;
  mt5Status?: MT5StatusInfo | null;
  riskStatus?: RiskStatus | null;
  onReconnectMt5: () => Promise<void>;
}

export const Navbar: React.FC<NavbarProps> = ({
  botState,
  mt5Status,
  riskStatus,
  onReconnectMt5,
}) => {
  const [currentTime, setCurrentTime] = useState<string>("");
  const [isReconnecting, setIsReconnecting] = useState<boolean>(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toISOString().substring(11, 19) + " UTC"
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleReconnect = async () => {
    setIsReconnecting(true);
    try {
      await onReconnectMt5();
    } finally {
      setIsReconnecting(false);
    }
  };

  const isConnected = mt5Status?.connected ?? false;
  const isDemo = mt5Status?.is_demo ?? true;
  const loginNum = mt5Status?.account_info?.login;
  const serverName = mt5Status?.account_info?.server;

  return (
    <header className="top-navbar">
      <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #0284c7 0%, #00f0ff 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 15px rgba(0, 240, 255, 0.4)",
            }}
          >
            <Cpu size={19} color="#07090e" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: "1.05rem", letterSpacing: "0.03em" }}>
              <span className="text-gradient">TRADEPILOT</span>{" "}
              <span className="text-gradient-cyan">AI</span>
            </div>
          </div>
        </div>

        {/* Demo-Only & Live Safeguard Badges */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span className="badge badge-demo">
            <ShieldCheck size={13} />
            DEMO ONLY
          </span>
          <span className="badge badge-live-blocked">
            <ShieldAlert size={13} />
            LIVE BLOCKED
          </span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        {/* Risk Lock Indicator */}
        {riskStatus?.is_locked && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <StatusBadge type="risk" value="LOCKED" />
          </div>
        )}

        {/* Bot State */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>BOT:</span>
          <StatusBadge type="bot_state" value={botState?.current_state || "IDLE"} />
        </div>

        {/* MT5 Connection Pill */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.35rem 0.75rem",
            background: isConnected ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)",
            border: `1px solid ${isConnected ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
            borderRadius: "9999px",
            fontSize: "0.78rem",
          }}
        >
          <Activity size={13} color={isConnected ? "#10b981" : "#ef4444"} />
          <span style={{ color: isConnected ? "#34d399" : "#f87171", fontWeight: 600 }}>
            {isConnected
              ? `MT5 Demo #${loginNum || "81879914"} (${serverName || "Exness"})`
              : "MT5 Disconnected"}
          </span>
          <button
            onClick={handleReconnect}
            disabled={isReconnecting}
            title="Reconnect MT5"
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-secondary)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              padding: "2px",
              marginLeft: "4px",
            }}
          >
            <RefreshCw size={13} className={isReconnecting ? "spin" : ""} />
          </button>
        </div>

        {/* Live UTC Clock */}
        <div
          className="tabular-nums"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
            fontSize: "0.8rem",
            color: "var(--text-secondary)",
            background: "rgba(255, 255, 255, 0.03)",
            padding: "0.35rem 0.65rem",
            borderRadius: "6px",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <Clock size={13} />
          <span>{currentTime}</span>
        </div>
      </div>
    </header>
  );
};
