import React, { useState, useEffect } from "react";
import {
  BarChart3,
  Download,
  FileSpreadsheet,
  Calendar,
  TrendingUp,
  Award,
  Play,
  Info,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { ReportSummary, BacktestResult } from "../types";
import { api } from "../services/api";
import { MetricCard } from "../components/MetricCard";

export const ReportsAnalyticsPage: React.FC = () => {
  const [period, setPeriod] = useState<"daily" | "weekly" | "monthly" | "all_time">("daily");
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Backtest state
  const [backtestDays, setBacktestDays] = useState<number>(14);
  const [backtestStrategy, setBacktestStrategy] = useState<string>("adaptive");
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [isRunningBacktest, setIsRunningBacktest] = useState<boolean>(false);

  const fetchReport = async (p = period) => {
    setIsLoading(true);
    try {
      const data = await api.getReportSummary(p);
      setReport(data);
    } catch (err) {
      console.error("Failed to load report summary:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReport(period);
  }, [period]);

  const handleRunBacktest = async () => {
    setIsRunningBacktest(true);
    try {
      const res = await api.runBacktest({
        symbol: "EURUSD",
        timeframe: "M15",
        lookback_days: backtestDays,
        strategy_mode: backtestStrategy,
        initial_balance: 10000.0,
      });
      setBacktestResult(res);
    } catch (err) {
      console.error("Backtest failed:", err);
    } finally {
      setIsRunningBacktest(false);
    }
  };

  const metrics = report?.metrics;
  const netPnL = metrics?.net_pnl ?? 0;
  const winRate = metrics?.win_rate ?? 0;
  const profitFactor = metrics?.profit_factor ?? 0;
  const totalTrades = metrics?.total_trades ?? 0;
  const maxDd = metrics?.max_drawdown_pct ?? 0;
  const expectancy = metrics?.trade_expectancy ?? 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header and Period Selector */}
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
            <BarChart3 size={24} color="#07090e" />
          </div>
          <div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 800 }}>Performance & Reporting</h2>
            <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
              Institutional grade analytics, exportable PDF audit reports, and backtests
            </div>
          </div>
        </div>

        {/* Period Selector & Download Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          <div
            style={{
              display: "flex",
              background: "rgba(255, 255, 255, 0.04)",
              borderRadius: "var(--radius-md)",
              padding: "2px",
              border: "1px solid var(--border-subtle)",
            }}
          >
            {(["daily", "weekly", "monthly", "all_time"] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                style={{
                  padding: "0.45rem 0.85rem",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  borderRadius: "6px",
                  border: "none",
                  cursor: "pointer",
                  background: period === p ? "#38bdf8" : "transparent",
                  color: period === p ? "#07090e" : "var(--text-secondary)",
                  transition: "all 0.15s ease",
                  textTransform: "capitalize",
                }}
              >
                {p.replace("_", " ")}
              </button>
            ))}
          </div>

          {/* PDF Download Button */}
          <a
            href={api.getPdfUrl(period)}
            target="_blank"
            rel="noreferrer"
            className="btn btn-primary"
            style={{ padding: "0.45rem 0.85rem", fontSize: "0.8rem", textDecoration: "none" }}
          >
            <Download size={14} />
            <span>Export PDF</span>
          </a>

          {/* CSV Download Button */}
          <a
            href={api.getCsvUrl(period)}
            target="_blank"
            rel="noreferrer"
            className="btn btn-secondary"
            style={{ padding: "0.45rem 0.85rem", fontSize: "0.8rem", textDecoration: "none" }}
          >
            <FileSpreadsheet size={14} />
            <span>Export CSV</span>
          </a>
        </div>
      </div>

      {/* Primary KPI Metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1rem",
        }}
      >
        <MetricCard
          title="Net Realized PnL"
          value={`${netPnL >= 0 ? "+" : ""}$${netPnL.toFixed(2)}`}
          subValue={period.toUpperCase() + " Period Total"}
          trend={netPnL >= 0 ? "up" : "down"}
          accentColor={netPnL >= 0 ? "green" : "red"}
        />
        <MetricCard
          title="Win Rate"
          value={`${winRate.toFixed(1)}%`}
          subValue={`${metrics?.winning_trades || 0}W / ${metrics?.losing_trades || 0}L`}
          accentColor="cyan"
        />
        <MetricCard
          title="Profit Factor"
          value={profitFactor > 50 ? "50.00+" : profitFactor.toFixed(2)}
          subValue={`Gross: +$${(metrics?.gross_profit || 0).toFixed(2)}`}
          accentColor="purple"
        />
        <MetricCard
          title="Max Drawdown"
          value={`${maxDd.toFixed(2)}%`}
          subValue={`Amount: $${(metrics?.max_drawdown_amount || 0).toFixed(2)}`}
          accentColor={maxDd > 3.0 ? "red" : "cyan"}
        />
        <MetricCard
          title="Trade Expectancy"
          value={`${expectancy.toFixed(2)} R`}
          subValue={`Avg Win: $${(metrics?.average_win || 0).toFixed(2)}`}
          accentColor="green"
        />
      </div>

      {/* Breakdown by Strategy & Regime */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
        {/* Strategy Breakdown */}
        <div className="glass-panel" style={{ padding: "1.25rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.75rem" }}>
            Performance by Strategy
          </h3>
          {metrics?.performance_by_strategy && Object.keys(metrics.performance_by_strategy).length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {Object.entries(metrics.performance_by_strategy).map(([strat, data]: [string, any]) => (
                <div
                  key={strat}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "0.65rem 0.85rem",
                    background: "rgba(255, 255, 255, 0.02)",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "0.825rem",
                  }}
                >
                  <span style={{ fontWeight: 600, color: "#c084fc" }}>{strat}</span>
                  <div style={{ display: "flex", gap: "1.25rem" }}>
                    <span>{data.trades} trades</span>
                    <strong
                      className="tabular-nums"
                      style={{ color: data.net_pnl >= 0 ? "var(--color-bullish)" : "var(--color-bearish)" }}
                    >
                      {data.net_pnl >= 0 ? "+" : ""}${data.net_pnl?.toFixed(2)}
                    </strong>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "1.5rem" }}>
              No closed trade records for strategy attribution in this period.
            </div>
          )}
        </div>

        {/* Regime Breakdown */}
        <div className="glass-panel" style={{ padding: "1.25rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.75rem" }}>
            Performance by Market Regime
          </h3>
          {metrics?.performance_by_regime && Object.keys(metrics.performance_by_regime).length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {Object.entries(metrics.performance_by_regime).map(([reg, data]: [string, any]) => (
                <div
                  key={reg}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "0.65rem 0.85rem",
                    background: "rgba(255, 255, 255, 0.02)",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "0.825rem",
                  }}
                >
                  <span style={{ fontWeight: 600, color: "#38bdf8", textTransform: "capitalize" }}>
                    {reg}
                  </span>
                  <div style={{ display: "flex", gap: "1.25rem" }}>
                    <span>{data.trades} trades</span>
                    <strong
                      className="tabular-nums"
                      style={{ color: data.net_pnl >= 0 ? "var(--color-bullish)" : "var(--color-bearish)" }}
                    >
                      {data.net_pnl >= 0 ? "+" : ""}${data.net_pnl?.toFixed(2)}
                    </strong>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "1.5rem" }}>
              No closed trade records for regime attribution in this period.
            </div>
          )}
        </div>
      </div>

      {/* Historical Backtester Simulator */}
      <div className="glass-panel" style={{ padding: "1.25rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1rem",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Play size={18} color="#10b981" />
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700 }}>Strategy Backtester Simulator</h3>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Run deterministic backtest on historical MT5 EUR/USD candles
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <select
              value={backtestStrategy}
              onChange={(e) => setBacktestStrategy(e.target.value)}
              className="form-select"
              style={{ width: "160px", fontSize: "0.8rem", padding: "0.45rem" }}
            >
              <option value="adaptive">Adaptive Engine</option>
              <option value="trend_following">Trend-Following</option>
              <option value="range_bound">Range-Bound</option>
            </select>

            <select
              value={backtestDays}
              onChange={(e) => setBacktestDays(Number(e.target.value))}
              className="form-select"
              style={{ width: "130px", fontSize: "0.8rem", padding: "0.45rem" }}
            >
              <option value={7}>Last 7 Days</option>
              <option value={14}>Last 14 Days</option>
              <option value={30}>Last 30 Days</option>
              <option value={60}>Last 60 Days</option>
            </select>

            <button
              onClick={handleRunBacktest}
              disabled={isRunningBacktest}
              className="btn btn-primary"
              style={{ padding: "0.45rem 1rem", fontSize: "0.8rem" }}
            >
              <Play size={14} />
              <span>{isRunningBacktest ? "Simulating..." : "Run Backtest"}</span>
            </button>
          </div>
        </div>

        {backtestResult && (
          <div
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              padding: "1rem",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                gap: "0.75rem",
                marginBottom: "1rem",
              }}
            >
              <div>
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Simulated PnL:</span>
                <div
                  className="tabular-nums"
                  style={{
                    fontSize: "1.1rem",
                    fontWeight: 700,
                    color: backtestResult.net_pnl >= 0 ? "var(--color-bullish)" : "var(--color-bearish)",
                  }}
                >
                  {backtestResult.net_pnl >= 0 ? "+" : ""}${backtestResult.net_pnl.toFixed(2)}
                </div>
              </div>

              <div>
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Total Trades:</span>
                <div className="tabular-nums" style={{ fontSize: "1.1rem", fontWeight: 700 }}>
                  {backtestResult.metrics.total_trades}
                </div>
              </div>

              <div>
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Win Rate:</span>
                <div className="tabular-nums" style={{ fontSize: "1.1rem", fontWeight: 700, color: "#38bdf8" }}>
                  {backtestResult.metrics.win_rate.toFixed(1)}%
                </div>
              </div>

              <div>
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Profit Factor:</span>
                <div className="tabular-nums" style={{ fontSize: "1.1rem", fontWeight: 700 }}>
                  {backtestResult.metrics.profit_factor.toFixed(2)}
                </div>
              </div>

              <div>
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Max Drawdown:</span>
                <div className="tabular-nums" style={{ fontSize: "1.1rem", fontWeight: 700, color: "#f87171" }}>
                  {backtestResult.metrics.max_drawdown_pct.toFixed(2)}%
                </div>
              </div>
            </div>

            {backtestResult.data_limitations && backtestResult.data_limitations.length > 0 && (
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                <strong>Simulation Disclaimers:</strong> {backtestResult.data_limitations.join(" • ")}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Section 8 Mandated Transparent Limitations Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "1rem",
          background: "rgba(56, 189, 248, 0.04)",
          border: "1px solid rgba(56, 189, 248, 0.2)",
          display: "flex",
          alignItems: "flex-start",
          gap: "0.75rem",
          fontSize: "0.78rem",
          color: "var(--text-secondary)",
          lineHeight: 1.5,
        }}
      >
        <Info size={18} color="#38bdf8" style={{ marginTop: "2px", flexShrink: 0 }} />
        <div>
          <strong style={{ color: "#38bdf8" }}>Institutional Reporting Disclaimer:</strong> All data represents demo-only simulated execution. Forex spot execution in demo environments does not replicate real liquidity provider slippage, overnight rollover swap variance, or spread widening during high-impact macroeconomic news releases. Past performance does not guarantee future results.
        </div>
      </div>
    </div>
  );
};
