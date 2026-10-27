import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  ColorType,
  Time,
  IChartApi,
  ISeriesApi,
} from "lightweight-charts";
import { CandleData, IndicatorValues } from "../types";

interface TradingChartProps {
  candles: CandleData[];
  indicators?: IndicatorValues | null;
  symbol: string;
  timeframe: string;
  onTimeframeChange?: (tf: string) => void;
  height?: number;
}

export const TradingChart: React.FC<TradingChartProps> = ({
  candles,
  indicators,
  symbol,
  timeframe,
  onTimeframeChange,
  height = 420,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const emaFastSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const emaSlowSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  const [hoveredCandle, setHoveredCandle] = useState<CandleData | null>(null);
  const [showIndicators, setShowIndicators] = useState<boolean>(true);

  const timeframes = ["M1", "M5", "M15", "H1", "D1"];

  // Initialize Chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "#0d121d" },
        textColor: "#94a3b8",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(25, 37, 59, 0.4)" },
        horzLines: { color: "rgba(25, 37, 59, 0.4)" },
      },
      crosshair: {
        vertLine: {
          color: "#38bdf8",
          width: 1,
          style: 3,
          labelBackgroundColor: "#1e293b",
        },
        horzLine: {
          color: "#38bdf8",
          width: 1,
          style: 3,
          labelBackgroundColor: "#1e293b",
        },
      },
      rightPriceScale: {
        borderColor: "rgba(25, 37, 59, 0.8)",
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "rgba(25, 37, 59, 0.8)",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    const emaFastSeries = chart.addSeries(LineSeries, {
      color: "#38bdf8",
      lineWidth: 2,
      title: "EMA 20",
    });

    const emaSlowSeries = chart.addSeries(LineSeries, {
      color: "#f59e0b",
      lineWidth: 2,
      title: "EMA 50",
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    emaFastSeriesRef.current = emaFastSeries;
    emaSlowSeriesRef.current = emaSlowSeries;

    // Crosshair move handler
    chart.subscribeCrosshairMove((param) => {
      if (!param || !param.time || !param.seriesData.get(candleSeries)) {
        setHoveredCandle(null);
        return;
      }
      const data = param.seriesData.get(candleSeries) as any;
      if (data) {
        setHoveredCandle({
          time: Number(param.time),
          open: data.open,
          high: data.high,
          low: data.low,
          close: data.close,
          volume: 0,
        });
      }
    });

    // Resize observer
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [height]);

  // Update Data
  useEffect(() => {
    if (!candleSeriesRef.current || candles.length === 0) return;

    // Sort and deduplicate candles by timestamp
    const sorted = [...candles].sort((a, b) => a.time - b.time);
    const uniqueCandles: CandleData[] = [];
    const seenTimes = new Set<number>();

    for (const c of sorted) {
      if (!seenTimes.has(c.time)) {
        seenTimes.add(c.time);
        uniqueCandles.push(c);
      }
    }

    const formattedCandles = uniqueCandles.map((c) => ({
      time: (c.time > 1000000000000 ? Math.floor(c.time / 1000) : c.time) as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    candleSeriesRef.current.setData(formattedCandles);

    // Calculate or render simple moving averages for indicators if enabled
    if (showIndicators && emaFastSeriesRef.current && emaSlowSeriesRef.current && formattedCandles.length > 50) {
      const fastPeriod = 20;
      const slowPeriod = 50;

      const calcEma = (period: number) => {
        const k = 2 / (period + 1);
        const res: Array<{ time: Time; value: number }> = [];
        let ema = formattedCandles[0].close;

        for (let i = 0; i < formattedCandles.length; i++) {
          const price = formattedCandles[i].close;
          if (i === 0) {
            ema = price;
          } else {
            ema = price * k + ema * (1 - k);
          }
          if (i >= period - 1) {
            res.push({
              time: formattedCandles[i].time,
              value: Number(ema.toFixed(5)),
            });
          }
        }
        return res;
      };

      emaFastSeriesRef.current.setData(calcEma(fastPeriod));
      emaSlowSeriesRef.current.setData(calcEma(slowPeriod));
    } else {
      emaFastSeriesRef.current?.setData([]);
      emaSlowSeriesRef.current?.setData([]);
    }

    // Auto-fit content once initial data arrives
    chartRef.current?.timeScale().fitContent();
  }, [candles, showIndicators]);

  const lastCandle = candles.length > 0 ? candles[candles.length - 1] : null;
  const activeCandle = hoveredCandle || lastCandle;

  return (
    <div className="glass-panel" style={{ padding: "1rem", display: "flex", flexDirection: "column" }}>
      {/* Top Chart Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "0.75rem",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.4rem" }}>
            <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-highlight)" }}>
              {symbol}
            </span>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Forex Spot</span>
          </div>

          {/* Timeframe Buttons */}
          <div
            style={{
              display: "flex",
              gap: "2px",
              background: "rgba(255, 255, 255, 0.04)",
              borderRadius: "6px",
              padding: "2px",
              border: "1px solid var(--border-subtle)",
            }}
          >
            {timeframes.map((tf) => (
              <button
                key={tf}
                onClick={() => onTimeframeChange?.(tf)}
                style={{
                  padding: "0.25rem 0.55rem",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  borderRadius: "4px",
                  border: "none",
                  cursor: "pointer",
                  background: timeframe === tf ? "#38bdf8" : "transparent",
                  color: timeframe === tf ? "#07090e" : "var(--text-secondary)",
                  transition: "all 0.15s ease",
                }}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Indicator Toggle */}
          <button
            onClick={() => setShowIndicators(!showIndicators)}
            className="btn btn-secondary"
            style={{ padding: "0.25rem 0.6rem", fontSize: "0.75rem" }}
          >
            {showIndicators ? "Hide Indicators" : "Show EMA 20/50"}
          </button>
        </div>

        {/* OHLC Values display */}
        {activeCandle && (
          <div
            className="tabular-nums"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.85rem",
              fontSize: "0.78rem",
              color: "var(--text-secondary)",
            }}
          >
            <span>
              O: <strong style={{ color: "var(--text-primary)" }}>{activeCandle.open.toFixed(5)}</strong>
            </span>
            <span>
              H: <strong style={{ color: "var(--color-bullish)" }}>{activeCandle.high.toFixed(5)}</strong>
            </span>
            <span>
              L: <strong style={{ color: "var(--color-bearish)" }}>{activeCandle.low.toFixed(5)}</strong>
            </span>
            <span>
              C:{" "}
              <strong
                style={{
                  color:
                    activeCandle.close >= activeCandle.open
                      ? "var(--color-bullish)"
                      : "var(--color-bearish)",
                }}
              >
                {activeCandle.close.toFixed(5)}
              </strong>
            </span>
            {indicators?.rsi && (
              <span style={{ color: "#a855f7" }}>
                RSI: <strong>{indicators.rsi.toFixed(1)}</strong>
              </span>
            )}
            {indicators?.atr && (
              <span style={{ color: "#38bdf8" }}>
                ATR: <strong>{indicators.atr.toFixed(5)}</strong>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Chart Canvas */}
      <div ref={chartContainerRef} style={{ width: "100%", height: `${height}px`, position: "relative" }} />
    </div>
  );
};
