import React, { useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Lock,
  Unlock,
  AlertTriangle,
  Activity,
  Calculator,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";
import { RiskStatus } from "../types";
import { MetricCard } from "../components/MetricCard";
import { ConfirmModal } from "../components/ConfirmModal";

interface RiskManagementPageProps {
  riskStatus?: RiskStatus | null;
  onResetRiskLock: () => Promise<void>;
  onRefresh: () => Promise<void>;
}

export const RiskManagementPage: React.FC<RiskManagementPageProps> = ({
  riskStatus,
  onResetRiskLock,
  onRefresh,
}) => {
  const [showUnlockModal, setShowUnlockModal] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [calcSlPips, setCalcSlPips] = useState<number>(20);

  const equity = riskStatus?.account_equity ?? 10000;
  const isLocked = riskStatus?.is_locked ?? false;
  const lockReason = riskStatus?.lock_reason;

  // Calculators
  const riskAmount = (equity * 0.0025); // 0.25% fixed
  // For EURUSD: 1 pip on 1 standard lot = $10. Lot = Risk / (SL pips * 10)
  const calculatedLots = calcSlPips > 0 ? (riskAmount / (calcSlPips * 10)).toFixed(2) : "0.01";

  const handleUnlock = async () => {
    setIsResetting(true);
    try {
      await onResetRiskLock();
    } finally {
      setIsResetting(false);
      setShowUnlockModal(false);
    }
  };

  const dailyLossPct = riskStatus?.daily_loss_pct ?? 0;
  const maxDailyLoss = riskStatus?.max_daily_loss_pct ?? 1.0;
  const weeklyLossPct = riskStatus?.weekly_loss_pct ?? 0;
  const maxWeeklyLoss = riskStatus?.max_weekly_loss_pct ?? 3.0;
  const consecutiveLosses = riskStatus?.consecutive_losses ?? 0;
  const maxConsecutive = riskStatus?.max_consecutive_losses ?? 3;
  const tradesToday = riskStatus?.trades_today ?? 0;
  const maxTrades = riskStatus?.max_trades_per_day ?? 5;
  const spread = riskStatus?.spread_pips ?? 0;
  const maxSpread = riskStatus?.max_spread_pips ?? 2.5;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Risk Lock Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "1.25rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
          background: isLocked ? "rgba(239, 68, 68, 0.1)" : "rgba(16, 185, 129, 0.08)",
          borderColor: isLocked ? "rgba(239, 68, 68, 0.4)" : "rgba(16, 185, 129, 0.3)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "12px",
              background: isLocked ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: isLocked ? "#ef4444" : "#10b981",
            }}
          >
            {isLocked ? <Lock size={22} /> : <ShieldCheck size={22} />}
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "1.2rem", fontWeight: 800 }}>
                {isLocked ? "SAFETY CIRCUIT BREAKER ACTIVE" : "ALL RISK SAFEGUARDS ACTIVE"}
              </h2>
              <span className={`badge ${isLocked ? "badge-bearish" : "badge-bullish"}`}>
                {isLocked ? "TRADING HALTED" : "PROTECTED"}
              </span>
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
              {isLocked
                ? `Lock Reason: ${lockReason || "Capital protection triggered"}`
                : "Deterministic rules enforcing 0.25% sizing, 1.0% daily cap, and consecutive loss limits."}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {isLocked && (
            <button
              onClick={() => setShowUnlockModal(true)}
              className="btn btn-danger"
              style={{ padding: "0.55rem 1.1rem" }}
            >
              <Unlock size={16} />
              <span>Reset Risk Lock</span>
            </button>
          )}
          <button
            onClick={onRefresh}
            className="btn btn-secondary"
            title="Refresh Risk Status"
            style={{ padding: "0.55rem 0.85rem" }}
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "1rem",
        }}
      >
        <MetricCard
          title="Risk Per Trade (Fixed)"
          value="0.25%"
          subValue={`$${riskAmount.toFixed(2)} per position`}
          icon={Activity}
          accentColor="cyan"
        />
        <MetricCard
          title="Daily Loss Progress"
          value={`${dailyLossPct.toFixed(2)}% / ${maxDailyLoss}%`}
          subValue={`${((dailyLossPct / maxDailyLoss) * 100).toFixed(0)}% of max daily limit`}
          icon={ShieldAlert}
          accentColor={dailyLossPct > 0.8 ? "red" : "green"}
          trend={dailyLossPct > 0.8 ? "down" : "neutral"}
        />
        <MetricCard
          title="Weekly Loss Progress"
          value={`${weeklyLossPct.toFixed(2)}% / ${maxWeeklyLoss}%`}
          subValue="Weekly drawdown circuit breaker"
          icon={ShieldAlert}
          accentColor={weeklyLossPct > 2.0 ? "red" : "green"}
        />
        <MetricCard
          title="Consecutive Loss Streak"
          value={`${consecutiveLosses} / ${maxConsecutive}`}
          subValue={consecutiveLosses >= 2 ? "Close to 3-loss pause" : "Healthy streak"}
          icon={AlertTriangle}
          accentColor={consecutiveLosses > 1 ? "amber" : "cyan"}
        />
      </div>

      {/* Circuit Breakers Detail Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "1.25rem" }}>
        {/* Left Column: Circuit Breaker Bars & Rejections */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="glass-panel" style={{ padding: "1.25rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "1rem" }}>
              Active Circuit Breakers & Thresholds
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {/* Daily Loss Progress Bar */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.825rem", marginBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Daily Loss Limit (1.0% hard halt)</span>
                  <strong className="tabular-nums" style={{ color: dailyLossPct > 0.8 ? "#ef4444" : "#10b981" }}>
                    {dailyLossPct.toFixed(2)}% / {maxDailyLoss}%
                  </strong>
                </div>
                <div style={{ height: "8px", background: "rgba(255, 255, 255, 0.08)", borderRadius: "4px", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.min(100, (dailyLossPct / maxDailyLoss) * 100)}%`,
                      background: dailyLossPct > 0.8 ? "#ef4444" : "#10b981",
                      transition: "width 0.3s ease",
                    }}
                  />
                </div>
              </div>

              {/* Weekly Loss Progress Bar */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.825rem", marginBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Weekly Loss Limit (3.0% hard halt)</span>
                  <strong className="tabular-nums" style={{ color: weeklyLossPct > 2.0 ? "#ef4444" : "#10b981" }}>
                    {weeklyLossPct.toFixed(2)}% / {maxWeeklyLoss}%
                  </strong>
                </div>
                <div style={{ height: "8px", background: "rgba(255, 255, 255, 0.08)", borderRadius: "4px", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.min(100, (weeklyLossPct / maxWeeklyLoss) * 100)}%`,
                      background: weeklyLossPct > 2.0 ? "#ef4444" : "#38bdf8",
                      transition: "width 0.3s ease",
                    }}
                  />
                </div>
              </div>

              {/* Trades Today */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.825rem", marginBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Trades Executed Today (Max 5/day)</span>
                  <strong className="tabular-nums" style={{ color: tradesToday >= 5 ? "#ef4444" : "var(--text-primary)" }}>
                    {tradesToday} / {maxTrades} trades
                  </strong>
                </div>
                <div style={{ height: "8px", background: "rgba(255, 255, 255, 0.08)", borderRadius: "4px", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.min(100, (tradesToday / maxTrades) * 100)}%`,
                      background: tradesToday >= 5 ? "#ef4444" : "#a855f7",
                      transition: "width 0.3s ease",
                    }}
                  />
                </div>
              </div>

              {/* Current Spread Check */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.825rem", marginBottom: "0.4rem" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Broker Spread Ceiling (Max 2.5 pips)</span>
                  <strong className="tabular-nums" style={{ color: spread > maxSpread ? "#ef4444" : "#10b981" }}>
                    {spread.toFixed(1)} / {maxSpread} pips
                  </strong>
                </div>
                <div style={{ height: "8px", background: "rgba(255, 255, 255, 0.08)", borderRadius: "4px", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.min(100, (spread / maxSpread) * 100)}%`,
                      background: spread > maxSpread ? "#ef4444" : "#10b981",
                      transition: "width 0.3s ease",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Rejection Reasons Log */}
          <div className="glass-panel" style={{ padding: "1.25rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.75rem" }}>
              Risk Engine Decision Log
            </h3>
            {riskStatus?.rejection_reasons && riskStatus.rejection_reasons.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {riskStatus.rejection_reasons.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.6rem",
                      padding: "0.6rem 0.85rem",
                      background: "rgba(239, 68, 68, 0.08)",
                      border: "1px solid rgba(239, 68, 68, 0.25)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "0.8rem",
                      color: "#f87171",
                    }}
                  >
                    <AlertTriangle size={15} style={{ flexShrink: 0 }} />
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  color: "#34d399",
                  fontSize: "0.85rem",
                  padding: "0.75rem 0",
                }}
              >
                <CheckCircle2 size={16} /> All risk gates open. New orders eligible when strategy conditions trigger.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Sizing & Capital Protection Calculator */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="glass-panel" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
              <Calculator size={18} color="#38bdf8" />
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Deterministic Position Sizer</h3>
            </div>

            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "1rem", lineHeight: 1.5 }}>
              Positions are sized deterministically from account equity using fixed 0.25% risk, ATR-based Stop Loss, and broker volume step quantization.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
              <div>
                <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "0.25rem" }}>
                  Account Equity ($)
                </label>
                <input
                  type="text"
                  disabled
                  value={`$${equity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                  className="form-input"
                  style={{ opacity: 0.8 }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "0.25rem" }}>
                  Fixed Risk Per Trade (0.25%)
                </label>
                <input
                  type="text"
                  disabled
                  value={`$${riskAmount.toFixed(2)}`}
                  className="form-input"
                  style={{ color: "#38bdf8", fontWeight: 600, opacity: 0.8 }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: "0.25rem" }}>
                  Stop Loss Distance: {calcSlPips} pips
                </label>
                <input
                  type="range"
                  min="10"
                  max="60"
                  value={calcSlPips}
                  onChange={(e) => setCalcSlPips(Number(e.target.value))}
                  style={{ width: "100%", accentColor: "#38bdf8" }}
                />
              </div>

              <div
                style={{
                  background: "rgba(56, 189, 248, 0.08)",
                  border: "1px solid rgba(56, 189, 248, 0.25)",
                  padding: "0.85rem",
                  borderRadius: "var(--radius-md)",
                  marginTop: "0.5rem",
                }}
              >
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                  Calculated Order Lot Size:
                </div>
                <div className="tabular-nums" style={{ fontSize: "1.4rem", fontWeight: 800, color: "#38bdf8" }}>
                  {calculatedLots} <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>Lots</span>
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
                  Rounded down to broker volume step (0.01)
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={showUnlockModal}
        title="Reset Risk Safety Lock"
        message="Are you sure you want to manually reset the risk lock? Ensure you have reviewed current market volatility, active news events, and account drawdown before resuming."
        confirmText="Reset and Unlock"
        isDangerous={true}
        onConfirm={handleUnlock}
        onCancel={() => setShowUnlockModal(false)}
      />
    </div>
  );
};
