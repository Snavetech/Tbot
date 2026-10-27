import React, { useState, useEffect } from "react";
import {
  Sliders,
  ShieldCheck,
  ShieldAlert,
  Server,
  Terminal,
  Play,
  Pause,
  Square,
  AlertTriangle,
  RefreshCw,
  Cpu,
  Layers,
  Save,
  CheckCircle2,
} from "lucide-react";
import {
  BotState,
  MT5StatusInfo,
  MT5AccountInfo,
  AppSettings,
  AuditEvent,
} from "../types";
import { api } from "../services/api";
import { StatusBadge } from "../components/StatusBadge";
import { ConfirmModal } from "../components/ConfirmModal";

interface SettingsHealthPageProps {
  botState?: BotState | null;
  mt5Status?: MT5StatusInfo | null;
  onStartBot: () => Promise<void>;
  onPauseBot: () => Promise<void>;
  onResumeBot: () => Promise<void>;
  onStopBot: () => Promise<void>;
  onEmergencyFlatten: () => Promise<void>;
  onReconnectMt5: () => Promise<void>;
}

export const SettingsHealthPage: React.FC<SettingsHealthPageProps> = ({
  botState,
  mt5Status,
  onStartBot,
  onPauseBot,
  onResumeBot,
  onStopBot,
  onEmergencyFlatten,
  onReconnectMt5,
}) => {
  const [accountInfo, setAccountInfo] = useState<MT5AccountInfo | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditEvent[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  // Modal states
  const [showFlattenModal, setShowFlattenModal] = useState<boolean>(false);
  const [showStopModal, setShowStopModal] = useState<boolean>(false);

  const fetchDiagnostics = async () => {
    try {
      const [acc, set, logs] = await Promise.all([
        api.getMt5Account().catch(() => null),
        api.getSettings().catch(() => null),
        api.getAuditLog(50).catch(() => []),
      ]);
      if (acc) setAccountInfo(acc);
      if (set) setSettings(set);
      if (logs) setAuditLogs(logs);
    } catch (err) {
      console.error("Error fetching settings diagnostics:", err);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  const handleSaveSettings = async () => {
    if (!settings) return;
    setIsSaving(true);
    try {
      await api.updateSettings(settings);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save settings:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const filteredLogs = auditLogs.filter(
    (log) => severityFilter === "ALL" || log.severity === severityFilter
  );

  const isConnected = mt5Status?.connected ?? false;
  const isDemo = mt5Status?.is_demo ?? true;
  const currentState = botState?.current_state || "IDLE";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div
        className="glass-panel"
        style={{
          padding: "1.25rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Sliders size={24} color="#07090e" />
          </div>
          <div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 800 }}>Settings & Diagnostics</h2>
            <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
              MetaTrader 5 gateway connection, autonomous engine state, and broker symbol parameters
            </div>
          </div>
        </div>

        <button
          onClick={fetchDiagnostics}
          className="btn btn-secondary"
          style={{ padding: "0.5rem 0.9rem", fontSize: "0.8rem" }}
        >
          <RefreshCw size={14} />
          <span>Refresh Diagnostics</span>
        </button>
      </div>

      {/* Autonomous Bot Operation Controls */}
      <div className="glass-panel" style={{ padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Cpu size={18} color="#00f0ff" />
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700 }}>Autonomous Bot Controller</h3>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Engine State:</span>
            <StatusBadge type="bot_state" value={currentState} />
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "1rem",
            background: "rgba(255, 255, 255, 0.02)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
              Last Transition Reason
            </div>
            <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
              {botState?.transition_reason || "System initialized"} • Time:{" "}
              {botState?.last_transition_time ? botState.last_transition_time.substring(11, 19) : "N/A"}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            {currentState !== "RUNNING" ? (
              <button
                onClick={onStartBot}
                className="btn btn-success"
                style={{ padding: "0.5rem 1rem", fontSize: "0.85rem" }}
              >
                <Play size={16} />
                <span>Start Engine</span>
              </button>
            ) : (
              <button
                onClick={onPauseBot}
                className="btn btn-secondary"
                style={{ padding: "0.5rem 1rem", fontSize: "0.85rem" }}
              >
                <Pause size={16} />
                <span>Pause</span>
              </button>
            )}

            {currentState === "PAUSED" && (
              <button
                onClick={onResumeBot}
                className="btn btn-primary"
                style={{ padding: "0.5rem 1rem", fontSize: "0.85rem" }}
              >
                <Play size={16} />
                <span>Resume</span>
              </button>
            )}

            <button
              onClick={() => setShowStopModal(true)}
              className="btn btn-secondary"
              style={{ padding: "0.5rem 1rem", fontSize: "0.85rem" }}
            >
              <Square size={16} />
              <span>Safe Stop</span>
            </button>

            <button
              onClick={() => setShowFlattenModal(true)}
              className="btn btn-danger"
              style={{ padding: "0.5rem 1rem", fontSize: "0.85rem" }}
            >
              <AlertTriangle size={16} />
              <span>Emergency Flatten</span>
            </button>
          </div>
        </div>
      </div>

      {/* MT5 Diagnostic Info */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
        {/* Terminal Connection */}
        <div className="glass-panel" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Terminal size={18} color="#38bdf8" />
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>MT5 Terminal Status</h3>
            </div>
            <button
              onClick={onReconnectMt5}
              className="btn btn-secondary"
              style={{ padding: "0.3rem 0.65rem", fontSize: "0.75rem" }}
            >
              Reconnect
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.825rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Connection:</span>
              <strong style={{ color: isConnected ? "var(--color-bullish)" : "var(--color-bearish)" }}>
                {isConnected ? "Connected to Desktop MT5" : "Disconnected"}
              </strong>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Mode:</span>
              <span className="badge badge-demo">DEMO ONLY</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Live Safeguard:</span>
              <span className="badge badge-live-blocked">LIVE TRADING BLOCKED</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Terminal Executable:</span>
              <span style={{ color: "var(--text-primary)", fontFamily: "monospace", fontSize: "0.75rem" }}>
                {mt5Status?.terminal_info?.name || "MetaTrader 5"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Algorithmic Trading Allowed:</span>
              <strong style={{ color: mt5Status?.terminal_info?.trade_allowed ? "var(--color-bullish)" : "var(--color-bearish)" }}>
                {mt5Status?.terminal_info?.trade_allowed ? "YES (Enabled)" : "NO (Blocked by Terminal)"}
              </strong>
            </div>
          </div>
        </div>

        {/* Account Details */}
        <div className="glass-panel" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            <Server size={18} color="#a855f7" />
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Broker Account Details</h3>
          </div>

          {accountInfo ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.825rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                <span style={{ color: "var(--text-muted)" }}>Login Account:</span>
                <strong className="tabular-nums">#{accountInfo.login}</strong>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                <span style={{ color: "var(--text-muted)" }}>Broker Server:</span>
                <span style={{ color: "var(--text-primary)" }}>{accountInfo.server}</span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                <span style={{ color: "var(--text-muted)" }}>Company:</span>
                <span style={{ color: "var(--text-primary)" }}>{accountInfo.company}</span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
                <span style={{ color: "var(--text-muted)" }}>Currency & Leverage:</span>
                <span style={{ color: "var(--text-primary)" }}>
                  {accountInfo.currency} (1:{accountInfo.leverage})
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Free Margin:</span>
                <strong className="tabular-nums" style={{ color: "#34d399" }}>
                  ${accountInfo.margin_free.toFixed(2)}
                </strong>
              </div>
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "1.5rem" }}>
              Account information unavailable. Check MT5 connection.
            </div>
          )}
        </div>
      </div>

      {/* Symbol Mapping & Parameters Form */}
      {settings && (
        <div className="glass-panel" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Execution Parameters & Symbol Mapping</h3>
            <button
              onClick={handleSaveSettings}
              disabled={isSaving}
              className="btn btn-primary"
              style={{ padding: "0.4rem 0.9rem", fontSize: "0.8rem" }}
            >
              <Save size={14} />
              <span>{isSaving ? "Saving..." : "Save Parameters"}</span>
            </button>
          </div>

          {saveSuccess && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                color: "#34d399",
                background: "rgba(16, 185, 129, 0.1)",
                padding: "0.5rem 0.75rem",
                borderRadius: "var(--radius-sm)",
                marginBottom: "1rem",
                fontSize: "0.8rem",
              }}
            >
              <CheckCircle2 size={16} /> Parameters saved successfully.
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "0.3rem" }}>
                Evaluated Forex Symbol
              </label>
              <input
                type="text"
                value={settings.allowed_symbols.join(", ")}
                disabled
                className="form-input"
                style={{ opacity: 0.8 }}
              />
            </div>

            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "0.3rem" }}>
                Broker Symbol Mapping (EURUSD)
              </label>
              <input
                type="text"
                value={settings.symbol_mapping["EURUSD"] || "EURUSDm"}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    symbol_mapping: { ...settings.symbol_mapping, EURUSD: e.target.value },
                  })
                }
                className="form-input"
              />
            </div>

            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "0.3rem" }}>
                Evaluation Interval (seconds)
              </label>
              <input
                type="number"
                min="10"
                max="3600"
                value={settings.decision_interval_seconds}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    decision_interval_seconds: Number(e.target.value),
                  })
                }
                className="form-input"
              />
            </div>
          </div>
        </div>
      )}

      {/* Audit Log Table */}
      <div className="glass-panel" style={{ padding: "1.25rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1rem",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>System Audit Trail</h3>

          <div style={{ display: "flex", gap: "4px" }}>
            {["ALL", "INFO", "WARNING", "ERROR", "CRITICAL"].map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                style={{
                  padding: "0.25rem 0.55rem",
                  fontSize: "0.72rem",
                  borderRadius: "4px",
                  border: "none",
                  cursor: "pointer",
                  background: severityFilter === sev ? "rgba(56, 189, 248, 0.2)" : "transparent",
                  color: severityFilter === sev ? "#38bdf8" : "var(--text-muted)",
                }}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        <div style={{ maxHeight: "320px", overflowY: "auto" }}>
          <table className="fintech-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Severity</th>
                <th>Event Type</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => (
                <tr key={log.id}>
                  <td className="tabular-nums" style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                    {log.timestamp ? log.timestamp.substring(11, 19) : "N/A"}
                  </td>
                  <td>
                    <StatusBadge type="severity" value={log.severity} size="sm" />
                  </td>
                  <td style={{ fontSize: "0.75rem", color: "#c084fc", fontWeight: 500 }}>
                    {log.event_type}
                  </td>
                  <td style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                    {log.message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Modals */}
      <ConfirmModal
        isOpen={showFlattenModal}
        title="Emergency Flatten All Positions"
        message="This will immediately submit market orders to close ALL active positions on the MT5 terminal. Are you sure you want to proceed?"
        confirmText="Flatten All"
        isDangerous={true}
        onConfirm={async () => {
          setShowFlattenModal(false);
          await onEmergencyFlatten();
        }}
        onCancel={() => setShowFlattenModal(false)}
      />

      <ConfirmModal
        isOpen={showStopModal}
        title="Safe Stop Engine"
        message="Safe Stop halts new order evaluation while continuing to monitor and protect open positions with SL/TP. Do you wish to stop the bot?"
        confirmText="Safe Stop"
        isDangerous={false}
        onConfirm={async () => {
          setShowStopModal(false);
          await onStopBot();
        }}
        onCancel={() => setShowStopModal(false)}
      />
    </div>
  );
};
