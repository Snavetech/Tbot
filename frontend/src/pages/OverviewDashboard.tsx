import React from "react";
import {
  Wallet,
  TrendingUp,
  Shield,
  Activity,
  AlertTriangle,
  BrainCircuit,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
} from "lucide-react";
import {
  BotState,
  RiskStatus,
  MarketOverview,
  AiDecisionOutput,
  Position,
  AuditEvent,
} from "../types";
import { MetricCard } from "../components/MetricCard";
import { StatusBadge } from "../components/StatusBadge";

interface OverviewDashboardProps {
  botState?: BotState | null;
  riskStatus?: RiskStatus | null;
  marketOverview?: MarketOverview | null;
  latestAnalysis?: AiDecisionOutput | null;
  positions: Position[];
  auditEvents: AuditEvent[];
  onNavigate: (page: any) => void;
  onClosePosition: (ticket: number) => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  botState,
  riskStatus,
  marketOverview,
  latestAnalysis,
  positions,
  auditEvents,
  onNavigate,
  onClosePosition,
}) => {
  const balance = riskStatus?.account_balance ?? 0;
  const equity = riskStatus?.account_equity ?? 0;
  const dailyLossPct = riskStatus?.daily_loss_pct ?? 0;
  const maxDailyLoss = riskStatus?.max_daily_loss_pct ?? 1.0;
  const consecutiveLosses = riskStatus?.consecutive_losses ?? 0;
  const maxConsecutive = riskStatus?.max_consecutive_losses ?? 3;
  const openRiskPct = riskStatus?.current_open_risk_pct ?? 0;
  const tradesToday = riskStatus?.trades_today ?? 0;
  const maxTrades = riskStatus?.max_trades_per_day ?? 5;

  const ticker = marketOverview?.ticker;
  const indicators = marketOverview?.indicators;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Top Alert Banner if Risk is Locked */}
      {riskStatus?.is_locked && (
        <div
          className="glass-panel"
          style={{
            background: "rgba(239, 68, 68, 0.12)",
            borderColor: "rgba(239, 68, 68, 0.4)",
            padding: "1rem 1.25rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <AlertTriangle size={20} color="#ef4444" />
            <div>
              <div style={{ fontWeight: 700, color: "#f87171", fontSize: "0.9rem" }}>
                RISK SAFETY LOCK TRIGGERED
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                {riskStatus.lock_reason || "Trading halted to protect capital."}
              </div>
            </div>
          </div>
          <button
            onClick={() => onNavigate("risk")}
            className="btn btn-secondary"
            style={{ fontSize: "0.8rem", padding: "0.4rem 0.8rem" }}
          >
            Review Risk Controls
          </button>
        </div>
      )}

      {/* KPI Metric Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "1rem",
        }}
      >
        <MetricCard
          title="Demo Balance"
          value={`$${balance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          subValue="Demo Account Equity Protected"
          icon={Wallet}
          accentColor="cyan"
        />
        <MetricCard
          title="Demo Equity"
          value={`$${equity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          subValue={equity >= balance ? "+ Profit Available" : "Floating Drawdown"}
          icon={TrendingUp}
          accentColor={equity >= balance ? "green" : "red"}
          trend={equity >= balance ? "up" : "down"}
        />
        <MetricCard
          title="Daily Loss Usage"
          value={`${dailyLossPct.toFixed(2)}% / ${maxDailyLoss}%`}
          subValue={`${(maxDailyLoss - dailyLossPct).toFixed(2)}% buffer remaining`}
          icon={Shield}
          accentColor={dailyLossPct > 0.7 ? "red" : "green"}
          trend={dailyLossPct > 0.7 ? "down" : "neutral"}
        />
        <MetricCard
          title="Open Risk"
          value={`${openRiskPct.toFixed(2)}%`}
          subValue={`Trades Today: ${tradesToday}/${maxTrades}`}
          icon={Activity}
          accentColor="purple"
        />
        <MetricCard
          title="Consecutive Losses"
          value={`${consecutiveLosses} / ${maxConsecutive}`}
          subValue={consecutiveLosses >= 2 ? "Warning: Near Limit" : "Normal state"}
          icon={AlertTriangle}
          accentColor={consecutiveLosses > 1 ? "amber" : "cyan"}
        />
      </div>

      {/* Main Grid: Market Snapshot & AI Analysis */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "1.25rem",
        }}
      >
        {/* Live Market Bar */}
        <div className="glass-panel" style={{ padding: "1.25rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Zap size={18} color="#00f0ff" />
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>EUR/USD Live Market</h3>
            </div>
            {indicators && <StatusBadge type="regime" value={indicators.regime} />}
          </div>

          {ticker ? (
            <div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: "0.75rem",
                  marginBottom: "1rem",
                  background: "rgba(255, 255, 255, 0.02)",
                  padding: "0.75rem",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Bid Price
                  </div>
                  <div className="tabular-nums" style={{ fontSize: "1.25rem", fontWeight: 700, color: "#38bdf8" }}>
                    {ticker.bid.toFixed(5)}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Ask Price
                  </div>
                  <div className="tabular-nums" style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>
                    {ticker.ask.toFixed(5)}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Spread
                  </div>
                  <div
                    className="tabular-nums"
                    style={{
                      fontSize: "1.25rem",
                      fontWeight: 700,
                      color: ticker.spread_pips > 2.0 ? "var(--color-bearish)" : "var(--color-bullish)",
                    }}
                  >
                    {ticker.spread_pips.toFixed(1)} <span style={{ fontSize: "0.75rem" }}>pips</span>
                  </div>
                </div>
              </div>

              {indicators && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.8rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-secondary)" }}>
                    <span>RSI (14):</span>
                    <strong className="tabular-nums" style={{ color: "var(--text-primary)" }}>
                      {indicators.rsi?.toFixed(1) ?? "N/A"}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-secondary)" }}>
                    <span>ATR (14):</span>
                    <strong className="tabular-nums" style={{ color: "var(--text-primary)" }}>
                      {indicators.atr?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-secondary)" }}>
                    <span>EMA 20:</span>
                    <strong className="tabular-nums" style={{ color: "#38bdf8" }}>
                      {indicators.ema_fast?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-secondary)" }}>
                    <span>EMA 50:</span>
                    <strong className="tabular-nums" style={{ color: "#f59e0b" }}>
                      {indicators.ema_slow?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", padding: "1.5rem 0", textAlign: "center" }}>
              Waiting for live ticker feed...
            </div>
          )}

          <div style={{ marginTop: "1rem", textAlign: "right" }}>
            <button
              onClick={() => onNavigate("terminal")}
              className="btn btn-secondary"
              style={{ fontSize: "0.8rem", padding: "0.4rem 0.8rem" }}
            >
              Open Trading Terminal <ArrowUpRight size={14} />
            </button>
          </div>
        </div>

        {/* Recent AI Strategy Decision */}
        <div className="glass-panel" style={{ padding: "1.25rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <BrainCircuit size={18} color="#a855f7" />
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Latest AI Decision</h3>
            </div>
            {latestAnalysis && <StatusBadge type="decision" value={latestAnalysis.decision} />}
          </div>

          {latestAnalysis ? (
            <div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "0.75rem",
                  background: "rgba(139, 92, 246, 0.08)",
                  border: "1px solid rgba(139, 92, 246, 0.2)",
                  padding: "0.6rem 0.85rem",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <div>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Strategy: </span>
                  <strong style={{ fontSize: "0.85rem", color: "#c084fc" }}>
                    {latestAnalysis.strategy || "None"}
                  </strong>
                </div>
                <div style={{ display: "flex", gap: "1rem" }}>
                  <div>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Confidence: </span>
                    <strong className="tabular-nums" style={{ fontSize: "0.85rem", color: "var(--text-primary)" }}>
                      {((latestAnalysis.confidence || 0) * 100).toFixed(0)}%
                    </strong>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Exp: </span>
                    <strong className="tabular-nums" style={{ fontSize: "0.85rem", color: "#34d399" }}>
                      {latestAnalysis.trade_expectancy?.toFixed(2) ?? "0.00"}R
                    </strong>
                  </div>
                </div>
              </div>

              <p
                style={{
                  fontSize: "0.825rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.5,
                  marginBottom: "0.75rem",
                  display: "-webkit-box",
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden",
                }}
              >
                {latestAnalysis.reasoning_summary}
              </p>

              {latestAnalysis.supporting_evidence && latestAnalysis.supporting_evidence.length > 0 && (
                <div style={{ fontSize: "0.78rem", color: "var(--color-bullish)", marginBottom: "0.25rem" }}>
                  ✓ {latestAnalysis.supporting_evidence[0]}
                </div>
              )}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", padding: "1.5rem 0", textAlign: "center" }}>
              Evaluating market conditions...
            </div>
          )}

          <div style={{ marginTop: "1rem", textAlign: "right" }}>
            <button
              onClick={() => onNavigate("analysis")}
              className="btn btn-secondary"
              style={{ fontSize: "0.8rem", padding: "0.4rem 0.8rem" }}
            >
              View Full AI Intelligence <ArrowUpRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Open Positions Section */}
      <div className="glass-panel" style={{ padding: "1.25rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Active Open Positions</h3>
            <span
              style={{
                fontSize: "0.75rem",
                padding: "0.15rem 0.5rem",
                borderRadius: "9999px",
                background: "rgba(56, 189, 248, 0.15)",
                color: "#38bdf8",
                fontWeight: 600,
              }}
            >
              {positions.length}
            </span>
          </div>

          <button
            onClick={() => onNavigate("positions")}
            className="btn btn-secondary"
            style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
          >
            All Trades & Orders
          </button>
        </div>

        {positions.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table className="fintech-table">
              <thead>
                <tr>
                  <th>Ticket</th>
                  <th>Symbol</th>
                  <th>Type</th>
                  <th>Volume</th>
                  <th>Open Price</th>
                  <th>Current</th>
                  <th>SL / TP</th>
                  <th>Floating PnL</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => {
                  const isProfit = pos.profit >= 0;
                  return (
                    <tr key={pos.ticket}>
                      <td className="tabular-nums">#{pos.ticket}</td>
                      <td style={{ fontWeight: 600 }}>{pos.symbol}</td>
                      <td>
                        <StatusBadge type="position_type" value={pos.position_type} size="sm" />
                      </td>
                      <td className="tabular-nums">{pos.volume.toFixed(2)}</td>
                      <td className="tabular-nums">{pos.open_price.toFixed(5)}</td>
                      <td className="tabular-nums">{pos.current_price.toFixed(5)}</td>
                      <td className="tabular-nums" style={{ fontSize: "0.75rem" }}>
                        {pos.sl.toFixed(5)} / {pos.tp.toFixed(5)}
                      </td>
                      <td
                        className="tabular-nums"
                        style={{
                          fontWeight: 700,
                          color: isProfit ? "var(--color-bullish)" : "var(--color-bearish)",
                        }}
                      >
                        {isProfit ? "+" : ""}${pos.profit.toFixed(2)}
                      </td>
                      <td>
                        <button
                          onClick={() => onClosePosition(pos.ticket)}
                          className="btn btn-danger"
                          style={{ padding: "0.25rem 0.55rem", fontSize: "0.75rem" }}
                        >
                          Close
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div
            style={{
              padding: "2rem",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: "0.875rem",
            }}
          >
            No active positions open. TradePilot AI evaluates trades autonomously when eligible.
          </div>
        )}
      </div>

      {/* System Audit Event Log */}
      <div className="glass-panel" style={{ padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Clock size={16} color="var(--text-secondary)" />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Recent Audit Activity</h3>
          </div>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            Real-time decision trail
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {auditEvents.slice(0, 5).map((ev) => (
            <div
              key={ev.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.5rem 0.75rem",
                background: "rgba(255, 255, 255, 0.02)",
                borderRadius: "6px",
                fontSize: "0.8rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <StatusBadge type="severity" value={ev.severity} size="sm" />
                <span style={{ color: "var(--text-primary)" }}>{ev.message}</span>
              </div>
              <span className="tabular-nums" style={{ color: "var(--text-muted)", fontSize: "0.72rem" }}>
                {ev.timestamp ? ev.timestamp.substring(11, 19) : ""}
              </span>
            </div>
          ))}
          {auditEvents.length === 0 && (
            <div style={{ color: "var(--text-muted)", fontSize: "0.8rem", textAlign: "center", padding: "1rem" }}>
              Audit events will appear as the engine runs.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
