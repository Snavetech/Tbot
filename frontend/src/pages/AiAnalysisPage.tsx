import React, { useState } from "react";
import {
  BrainCircuit,
  Zap,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  TrendingUp,
  Cpu,
  Sliders,
  History,
} from "lucide-react";
import { AiDecisionOutput } from "../types";
import { StatusBadge } from "../components/StatusBadge";
import { MetricCard } from "../components/MetricCard";

interface AiAnalysisPageProps {
  latestAnalysis?: AiDecisionOutput | null;
  history: AiDecisionOutput[];
  onTriggerEvaluation: () => Promise<void>;
}

export const AiAnalysisPage: React.FC<AiAnalysisPageProps> = ({
  latestAnalysis,
  history,
  onTriggerEvaluation,
}) => {
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    try {
      await onTriggerEvaluation();
    } finally {
      setIsEvaluating(false);
    }
  };

  const confidencePct = Math.round((latestAnalysis?.confidence ?? 0) * 100);
  const expectancy = latestAnalysis?.trade_expectancy ?? 0;
  const decision = latestAnalysis?.decision ?? "WAIT";
  const regime = latestAnalysis?.market_regime ?? "uncertain";
  const strategy = latestAnalysis?.strategy ?? "None (Awaiting conditions)";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header and Manual Evaluation Trigger */}
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
              background: "linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <BrainCircuit size={24} color="#fff" />
          </div>
          <div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 800 }}>AI Quantitative Analyst</h2>
            <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
              Multi-factor regime classifier & strategy selector (EUR/USD)
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <button
            onClick={handleEvaluate}
            disabled={isEvaluating}
            className="btn btn-primary"
            style={{ padding: "0.6rem 1.25rem" }}
          >
            <RefreshCw size={16} className={isEvaluating ? "spin" : ""} />
            <span>{isEvaluating ? "Evaluating..." : "Evaluate Market Now"}</span>
          </button>
        </div>
      </div>

      {/* Model Output Overview Metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "1rem",
        }}
      >
        <MetricCard
          title="Current Decision"
          value={decision}
          subValue={strategy}
          badge={<StatusBadge type="decision" value={decision} />}
          accentColor={decision === "BUY" ? "green" : decision === "SELL" ? "red" : "amber"}
          trend={decision === "BUY" ? "up" : decision === "SELL" ? "down" : "neutral"}
        />
        <MetricCard
          title="Detected Regime"
          value={regime.toUpperCase()}
          subValue="Classified by Multi-EMA & ATR"
          badge={<StatusBadge type="regime" value={regime} />}
          accentColor="purple"
        />
        <MetricCard
          title="Model Confidence"
          value={`${confidencePct}%`}
          subValue={confidencePct >= 70 ? "High statistical certainty" : "Moderate or neutral"}
          icon={Cpu}
          accentColor="cyan"
        />
        <MetricCard
          title="Trade Expectancy"
          value={`${expectancy.toFixed(2)} R`}
          subValue="Expected payout ratio"
          icon={TrendingUp}
          accentColor={expectancy > 0.5 ? "green" : "cyan"}
        />
      </div>

      {/* Deep-Dive Analysis Panel */}
      {latestAnalysis ? (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "1.25rem" }}>
          {/* Left Column: Natural Language Reasoning & Evidence */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Reasoning Summary Card */}
            <div className="glass-panel" style={{ padding: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <Zap size={18} color="#f59e0b" />
                <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Executive Reasoning Summary</h3>
              </div>
              <p
                style={{
                  fontSize: "0.9rem",
                  color: "var(--text-primary)",
                  lineHeight: 1.6,
                  background: "rgba(255, 255, 255, 0.02)",
                  padding: "1rem",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                {latestAnalysis.reasoning_summary}
              </p>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginTop: "0.75rem",
                  fontSize: "0.72rem",
                  color: "var(--text-muted)",
                }}
              >
                <span>Model: {latestAnalysis.model_version || "TradePilot-Ensemble-v1"}</span>
                <span>Evaluated: {latestAnalysis.feature_timestamp || "Just now"}</span>
              </div>
            </div>

            {/* Invalidation Conditions */}
            <div className="glass-panel" style={{ padding: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <AlertTriangle size={18} color="#f59e0b" />
                <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Trade Invalidation Conditions</h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {latestAnalysis.invalidation_conditions && latestAnalysis.invalidation_conditions.length > 0 ? (
                  latestAnalysis.invalidation_conditions.map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "0.6rem",
                        padding: "0.6rem 0.85rem",
                        background: "rgba(245, 158, 11, 0.06)",
                        border: "1px solid rgba(245, 158, 11, 0.2)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "0.825rem",
                        color: "#fbbf24",
                      }}
                    >
                      <AlertTriangle size={15} style={{ marginTop: "2px", flexShrink: 0 }} />
                      <span>{item}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                    No invalidation conditions specified.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Supporting vs Contradicting Evidence */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Supporting Evidence */}
            <div className="glass-panel" style={{ padding: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <CheckCircle2 size={18} color="#10b981" />
                <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "#34d399" }}>
                  Supporting Evidence ({latestAnalysis.supporting_evidence?.length || 0})
                </h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {latestAnalysis.supporting_evidence && latestAnalysis.supporting_evidence.length > 0 ? (
                  latestAnalysis.supporting_evidence.map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "0.6rem",
                        padding: "0.6rem 0.85rem",
                        background: "rgba(16, 185, 129, 0.06)",
                        border: "1px solid rgba(16, 185, 129, 0.2)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "0.825rem",
                        color: "var(--text-primary)",
                      }}
                    >
                      <CheckCircle2 size={15} color="#10b981" style={{ marginTop: "2px", flexShrink: 0 }} />
                      <span>{item}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                    No strong supporting evidence in current cycle.
                  </div>
                )}
              </div>
            </div>

            {/* Contradicting Evidence */}
            <div className="glass-panel" style={{ padding: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <XCircle size={18} color="#ef4444" />
                <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "#f87171" }}>
                  Contradicting Evidence ({latestAnalysis.contradicting_evidence?.length || 0})
                </h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {latestAnalysis.contradicting_evidence && latestAnalysis.contradicting_evidence.length > 0 ? (
                  latestAnalysis.contradicting_evidence.map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "0.6rem",
                        padding: "0.6rem 0.85rem",
                        background: "rgba(239, 68, 68, 0.06)",
                        border: "1px solid rgba(239, 68, 68, 0.2)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "0.825rem",
                        color: "var(--text-primary)",
                      }}
                    >
                      <XCircle size={15} color="#ef4444" style={{ marginTop: "2px", flexShrink: 0 }} />
                      <span>{item}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                    No contradicting factors detected.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-panel" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
          No model evaluations recorded yet. Click "Evaluate Market Now" to run analysis.
        </div>
      )}

      {/* Historical Evaluations Table */}
      <div className="glass-panel" style={{ padding: "1.25rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
          <History size={18} color="#38bdf8" />
          <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Recent AI Evaluation Log</h3>
        </div>

        {history && history.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table className="fintech-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Regime</th>
                  <th>Strategy</th>
                  <th>Decision</th>
                  <th>Confidence</th>
                  <th>Expectancy</th>
                  <th>Summary</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h, i) => (
                  <tr key={i}>
                    <td className="tabular-nums" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {h.feature_timestamp ? h.feature_timestamp.substring(11, 19) : "N/A"}
                    </td>
                    <td>
                      <StatusBadge type="regime" value={h.market_regime} size="sm" />
                    </td>
                    <td style={{ fontSize: "0.8rem", color: "#c084fc", fontWeight: 500 }}>
                      {h.strategy || "None"}
                    </td>
                    <td>
                      <StatusBadge type="decision" value={h.decision} size="sm" />
                    </td>
                    <td className="tabular-nums" style={{ fontWeight: 600 }}>
                      {((h.confidence || 0) * 100).toFixed(0)}%
                    </td>
                    <td className="tabular-nums" style={{ color: "#34d399", fontWeight: 600 }}>
                      {h.trade_expectancy?.toFixed(2) ?? "0.00"}R
                    </td>
                    <td
                      style={{
                        maxWidth: "320px",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        fontSize: "0.78rem",
                        color: "var(--text-secondary)",
                      }}
                      title={h.reasoning_summary}
                    >
                      {h.reasoning_summary}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "1.5rem" }}>
            History is empty. Evaluations will be logged periodically.
          </div>
        )}
      </div>
    </div>
  );
};
