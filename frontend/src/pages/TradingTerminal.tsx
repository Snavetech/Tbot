import React, { useState } from "react";
import {
  Activity,
  Layers,
  Zap,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  AlertCircle,
  Eye,
} from "lucide-react";
import {
  MarketOverview,
  CandleData,
  IndicatorValues,
  TickerData,
  Position,
} from "../types";
import { TradingChart } from "../components/TradingChart";
import { StatusBadge } from "../components/StatusBadge";

interface TradingTerminalProps {
  marketOverview?: MarketOverview | null;
  candles: CandleData[];
  indicators?: IndicatorValues | null;
  ticker?: TickerData | null;
  positions: Position[];
  timeframe: string;
  onTimeframeChange: (tf: string) => void;
  onClosePosition: (ticket: number) => void;
}

export const TradingTerminal: React.FC<TradingTerminalProps> = ({
  candles,
  indicators,
  ticker,
  positions,
  timeframe,
  onTimeframeChange,
  onClosePosition,
}) => {
  const [selectedTab, setSelectedTab] = useState<"chart" | "indicators" | "positions">("chart");

  const spreadPips = ticker?.spread_pips ?? 0;
  const isHighSpread = spreadPips > 2.0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Live Forex Quote Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "1rem 1.25rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <h2 style={{ fontSize: "1.3rem", fontWeight: 800 }}>EUR / USD</h2>
              <span className="badge badge-demo">Spot Demo</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Euro vs US Dollar • 1 Lot = 100,000 EUR
            </div>
          </div>
          {indicators && <StatusBadge type="regime" value={indicators.regime} />}
        </div>

        {/* Bid & Ask Price Display */}
        {ticker ? (
          <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
            {/* Bid Box */}
            <div
              style={{
                background: "rgba(56, 189, 248, 0.08)",
                border: "1px solid rgba(56, 189, 248, 0.3)",
                padding: "0.5rem 1rem",
                borderRadius: "var(--radius-md)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "0.7rem", color: "#38bdf8", fontWeight: 600 }}>BID</div>
              <div className="tabular-nums" style={{ fontSize: "1.4rem", fontWeight: 800, color: "#38bdf8" }}>
                {ticker.bid.toFixed(5)}
              </div>
            </div>

            {/* Spread Gauge */}
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                Spread
              </div>
              <div
                className="tabular-nums"
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 700,
                  color: isHighSpread ? "var(--color-bearish)" : "var(--color-bullish)",
                }}
              >
                {spreadPips.toFixed(1)}{" "}
                <span style={{ fontSize: "0.7rem", fontWeight: 500 }}>PIPS</span>
              </div>
              {isHighSpread && (
                <div style={{ fontSize: "0.65rem", color: "#f87171", display: "flex", alignItems: "center", gap: "2px" }}>
                  <AlertCircle size={10} /> Wide spread
                </div>
              )}
            </div>

            {/* Ask Box */}
            <div
              style={{
                background: "rgba(16, 185, 129, 0.08)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                padding: "0.5rem 1rem",
                borderRadius: "var(--radius-md)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "0.7rem", color: "#34d399", fontWeight: 600 }}>ASK</div>
              <div className="tabular-nums" style={{ fontSize: "1.4rem", fontWeight: 800, color: "#34d399" }}>
                {ticker.ask.toFixed(5)}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Connecting to broker quote stream...
          </div>
        )}
      </div>

      {/* Main Terminal Area */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "1.25rem" }}>
        {/* Left: Candlestick Chart */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <TradingChart
            candles={candles}
            indicators={indicators}
            symbol="EUR/USD"
            timeframe={timeframe}
            onTimeframeChange={onTimeframeChange}
            height={500}
          />

          {/* Active Positions on Symbol */}
          <div className="glass-panel" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Layers size={16} color="#38bdf8" />
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Open EUR/USD Positions</h3>
              </div>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {positions.length} position(s) active
              </span>
            </div>

            {positions.length > 0 ? (
              <div style={{ overflowX: "auto" }}>
                <table className="fintech-table">
                  <thead>
                    <tr>
                      <th>Ticket</th>
                      <th>Type</th>
                      <th>Volume</th>
                      <th>Open Price</th>
                      <th>Current</th>
                      <th>SL</th>
                      <th>TP</th>
                      <th>Floating PnL</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((p) => {
                      const isProfit = p.profit >= 0;
                      return (
                        <tr key={p.ticket}>
                          <td className="tabular-nums">#{p.ticket}</td>
                          <td>
                            <StatusBadge type="position_type" value={p.position_type} size="sm" />
                          </td>
                          <td className="tabular-nums">{p.volume.toFixed(2)}</td>
                          <td className="tabular-nums">{p.open_price.toFixed(5)}</td>
                          <td className="tabular-nums">{p.current_price.toFixed(5)}</td>
                          <td className="tabular-nums">{p.sl.toFixed(5)}</td>
                          <td className="tabular-nums">{p.tp.toFixed(5)}</td>
                          <td
                            className="tabular-nums"
                            style={{
                              fontWeight: 700,
                              color: isProfit ? "var(--color-bullish)" : "var(--color-bearish)",
                            }}
                          >
                            {isProfit ? "+" : ""}${p.profit.toFixed(2)}
                          </td>
                          <td>
                            <button
                              onClick={() => onClosePosition(p.ticket)}
                              className="btn btn-danger"
                              style={{ padding: "0.2rem 0.5rem", fontSize: "0.72rem" }}
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
              <div style={{ padding: "1rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                No active orders or open positions on EUR/USD.
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar: Technical Indicators & Signal Readings */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* Indicators Panel */}
          <div className="glass-panel" style={{ padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
              <Activity size={18} color="#00f0ff" />
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Market Analytics ({timeframe})</h3>
            </div>

            {indicators ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {/* RSI Gauge */}
                <div
                  style={{
                    background: "rgba(255, 255, 255, 0.02)",
                    padding: "0.85rem",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>RSI (14)</span>
                    <strong className="tabular-nums" style={{ fontSize: "0.9rem", color: "#a855f7" }}>
                      {indicators.rsi?.toFixed(1) ?? "N/A"}
                    </strong>
                  </div>

                  {/* Progress bar */}
                  <div
                    style={{
                      height: "6px",
                      background: "rgba(255, 255, 255, 0.1)",
                      borderRadius: "3px",
                      overflow: "hidden",
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min(100, Math.max(0, indicators.rsi ?? 50))}%`,
                        height: "100%",
                        background:
                          (indicators.rsi ?? 50) > 70
                            ? "#ef4444"
                            : (indicators.rsi ?? 50) < 30
                            ? "#10b981"
                            : "#a855f7",
                        transition: "width 0.3s ease",
                      }}
                    />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
                    <span>Oversold (30)</span>
                    <span>Neutral (50)</span>
                    <span>Overbought (70)</span>
                  </div>
                </div>

                {/* EMAs */}
                <div
                  style={{
                    background: "rgba(255, 255, 255, 0.02)",
                    padding: "0.85rem",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.4rem",
                  }}
                >
                  <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    Moving Averages
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>Fast EMA (20):</span>
                    <strong className="tabular-nums" style={{ color: "#38bdf8" }}>
                      {indicators.ema_fast?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>Slow EMA (50):</span>
                    <strong className="tabular-nums" style={{ color: "#f59e0b" }}>
                      {indicators.ema_slow?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                  {indicators.ema_fast && indicators.ema_slow && (
                    <div
                      style={{
                        fontSize: "0.72rem",
                        marginTop: "0.2rem",
                        color:
                          indicators.ema_fast > indicators.ema_slow
                            ? "var(--color-bullish)"
                            : "var(--color-bearish)",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.25rem",
                      }}
                    >
                      {indicators.ema_fast > indicators.ema_slow ? (
                        <>
                          <TrendingUp size={12} /> Bullish Alignment (EMA 20 &gt; 50)
                        </>
                      ) : (
                        <>
                          <TrendingDown size={12} /> Bearish Alignment (EMA 20 &lt; 50)
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Bollinger Bands & Volatility */}
                <div
                  style={{
                    background: "rgba(255, 255, 255, 0.02)",
                    padding: "0.85rem",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.4rem",
                  }}
                >
                  <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    Volatility & Ranges
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>ATR (14):</span>
                    <strong className="tabular-nums" style={{ color: "#00f0ff" }}>
                      {indicators.atr?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>BB Upper:</span>
                    <strong className="tabular-nums" style={{ color: "var(--text-secondary)" }}>
                      {indicators.bb_upper?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>BB Lower:</span>
                    <strong className="tabular-nums" style={{ color: "var(--text-secondary)" }}>
                      {indicators.bb_lower?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                </div>

                {/* Support & Resistance */}
                <div
                  style={{
                    background: "rgba(255, 255, 255, 0.02)",
                    padding: "0.85rem",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.4rem",
                  }}
                >
                  <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    Key Pivots
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>Resistance Level:</span>
                    <strong className="tabular-nums" style={{ color: "#f87171" }}>
                      {indicators.resistance_level?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>Support Level:</span>
                    <strong className="tabular-nums" style={{ color: "#34d399" }}>
                      {indicators.support_level?.toFixed(5) ?? "N/A"}
                    </strong>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ color: "var(--text-muted)", fontSize: "0.8rem", textAlign: "center", padding: "1.5rem" }}>
                Loading indicator calculations...
              </div>
            )}
          </div>

          {/* Autonomous Execution Note */}
          <div
            className="glass-panel"
            style={{
              padding: "1rem",
              background: "rgba(56, 189, 248, 0.05)",
              border: "1px solid rgba(56, 189, 248, 0.2)",
              fontSize: "0.75rem",
              color: "var(--text-secondary)",
              lineHeight: 1.5,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "#38bdf8", fontWeight: 600, marginBottom: "0.25rem" }}>
              <ShieldCheck size={14} /> Autonomous Demo Trading
            </div>
            TradePilot AI evaluates market conditions periodically and enters demo trades automatically when risk, ML probability, and strategy rules align.
          </div>
        </div>
      </div>
    </div>
  );
};
