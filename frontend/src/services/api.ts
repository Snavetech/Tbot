import {
  TickerData,
  CandleData,
  IndicatorValues,
  MarketOverview,
  AiDecisionOutput,
  Position,
  Order,
  Trade,
  BotState,
  RiskStatus,
  ReportSummary,
  BacktestResult,
  AuditEvent,
  HealthStatus,
  MT5StatusInfo,
  MT5AccountInfo,
  AppSettings,
} from "../types";

const BASE_URL = "";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // not JSON
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Health
  async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${BASE_URL}/api/health`);
    return handleResponse<HealthStatus>(res);
  },

  // MT5
  async getMt5Status(): Promise<MT5StatusInfo> {
    const res = await fetch(`${BASE_URL}/api/mt5/status`);
    return handleResponse<MT5StatusInfo>(res);
  },

  async reconnectMt5(): Promise<{ success: boolean; message: string; is_demo?: boolean }> {
    const res = await fetch(`${BASE_URL}/api/mt5/reconnect`, { method: "POST" });
    return handleResponse<{ success: boolean; message: string; is_demo?: boolean }>(res);
  },

  async getMt5Account(): Promise<MT5AccountInfo> {
    const res = await fetch(`${BASE_URL}/api/mt5/account`);
    return handleResponse<MT5AccountInfo>(res);
  },

  // Market Data
  async getTicker(symbol = "EURUSD"): Promise<TickerData> {
    const res = await fetch(`${BASE_URL}/api/market/ticker?symbol=${encodeURIComponent(symbol)}`);
    return handleResponse<TickerData>(res);
  },

  async getCandles(symbol = "EURUSD", timeframe = "M15", limit = 100): Promise<CandleData[]> {
    const res = await fetch(
      `${BASE_URL}/api/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=${limit}`
    );
    return handleResponse<CandleData[]>(res);
  },

  async getIndicators(symbol = "EURUSD", timeframe = "M15"): Promise<IndicatorValues> {
    const res = await fetch(
      `${BASE_URL}/api/market/indicators?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}`
    );
    return handleResponse<IndicatorValues>(res);
  },

  async getMarketOverview(symbol = "EURUSD", timeframe = "M15"): Promise<MarketOverview> {
    const res = await fetch(
      `${BASE_URL}/api/market/overview?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}`
    );
    return handleResponse<MarketOverview>(res);
  },

  // AI Analysis
  async getLatestAnalysis(symbol = "EURUSD"): Promise<AiDecisionOutput> {
    const res = await fetch(`${BASE_URL}/api/analysis/latest?symbol=${encodeURIComponent(symbol)}`);
    return handleResponse<AiDecisionOutput>(res);
  },

  async evaluateAnalysis(symbol = "EURUSD"): Promise<AiDecisionOutput> {
    const res = await fetch(`${BASE_URL}/api/analysis/evaluate?symbol=${encodeURIComponent(symbol)}`, {
      method: "POST",
    });
    return handleResponse<AiDecisionOutput>(res);
  },

  async getAnalysisHistory(symbol = "EURUSD", limit = 20): Promise<AiDecisionOutput[]> {
    const res = await fetch(
      `${BASE_URL}/api/analysis/history?symbol=${encodeURIComponent(symbol)}&limit=${limit}`
    );
    return handleResponse<AiDecisionOutput[]>(res);
  },

  // Bot State & Control
  async getBotState(): Promise<BotState> {
    const res = await fetch(`${BASE_URL}/api/bot/state`);
    return handleResponse<BotState>(res);
  },

  async startBot(): Promise<{ success: boolean; state: string; message: string }> {
    const res = await fetch(`${BASE_URL}/api/bot/start`, { method: "POST" });
    return handleResponse<{ success: boolean; state: string; message: string }>(res);
  },

  async pauseBot(): Promise<{ success: boolean; state: string; message: string }> {
    const res = await fetch(`${BASE_URL}/api/bot/pause`, { method: "POST" });
    return handleResponse<{ success: boolean; state: string; message: string }>(res);
  },

  async resumeBot(): Promise<{ success: boolean; state: string; message: string }> {
    const res = await fetch(`${BASE_URL}/api/bot/resume`, { method: "POST" });
    return handleResponse<{ success: boolean; state: string; message: string }>(res);
  },

  async stopBot(): Promise<{ success: boolean; state: string; message: string }> {
    const res = await fetch(`${BASE_URL}/api/bot/stop`, { method: "POST" });
    return handleResponse<{ success: boolean; state: string; message: string }>(res);
  },

  async getAuditLog(limit = 50): Promise<AuditEvent[]> {
    const res = await fetch(`${BASE_URL}/api/bot/audit-log?limit=${limit}`);
    return handleResponse<AuditEvent[]>(res);
  },

  // Positions & Trades
  async getPositions(): Promise<Position[]> {
    const res = await fetch(`${BASE_URL}/api/positions`);
    return handleResponse<Position[]>(res);
  },

  async closePosition(ticket: number, reason = "Manual UI close"): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${BASE_URL}/api/positions/close/${ticket}?reason=${encodeURIComponent(reason)}`, {
      method: "POST",
    });
    return handleResponse<{ success: boolean; message: string }>(res);
  },

  async emergencyFlatten(reason = "Emergency manual flatten from UI"): Promise<{
    success: boolean;
    closed_count: number;
    failed_count: number;
    errors: string[];
    results: any[];
  }> {
    const res = await fetch(
      `${BASE_URL}/api/positions/emergency-flatten?reason=${encodeURIComponent(reason)}`,
      { method: "POST" }
    );
    return handleResponse<{
      success: boolean;
      closed_count: number;
      failed_count: number;
      errors: string[];
      results: any[];
    }>(res);
  },

  async getTrades(limit = 50): Promise<Trade[]> {
    const res = await fetch(`${BASE_URL}/api/trades?limit=${limit}`);
    return handleResponse<Trade[]>(res);
  },

  async getOrders(limit = 50): Promise<Order[]> {
    const res = await fetch(`${BASE_URL}/api/orders?limit=${limit}`);
    return handleResponse<Order[]>(res);
  },

  // Risk
  async getRiskStatus(): Promise<RiskStatus> {
    const res = await fetch(`${BASE_URL}/api/risk/status`);
    return handleResponse<RiskStatus>(res);
  },

  async resetRiskLock(): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${BASE_URL}/api/risk/reset-lock`, { method: "POST" });
    return handleResponse<{ success: boolean; message: string }>(res);
  },

  // Backtest
  async runBacktest(params: {
    symbol?: string;
    timeframe?: string;
    lookback_days?: number;
    strategy_mode?: string;
    initial_balance?: number;
  }): Promise<BacktestResult> {
    const res = await fetch(`${BASE_URL}/api/backtest/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    return handleResponse<BacktestResult>(res);
  },

  // Reports
  async getReportSummary(period: "daily" | "weekly" | "monthly" | "all_time" = "daily"): Promise<ReportSummary> {
    const res = await fetch(`${BASE_URL}/api/reports/summary?period=${period}`);
    return handleResponse<ReportSummary>(res);
  },

  getPdfUrl(period: "daily" | "weekly" | "monthly" | "all_time" = "daily"): string {
    return `${BASE_URL}/api/reports/pdf?period=${period}`;
  },

  getCsvUrl(period: "daily" | "weekly" | "monthly" | "all_time" = "daily"): string {
    return `${BASE_URL}/api/reports/csv?period=${period}`;
  },

  // Settings
  async getSettings(): Promise<AppSettings> {
    const res = await fetch(`${BASE_URL}/api/settings`);
    return handleResponse<AppSettings>(res);
  },

  async updateSettings(settings: Partial<AppSettings>): Promise<{ success: boolean; settings: AppSettings }> {
    const res = await fetch(`${BASE_URL}/api/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    return handleResponse<{ success: boolean; settings: AppSettings }>(res);
  },
};
