// TypeScript definitions matching TradePilot AI backend schemas

export interface TickerData {
  symbol: string;
  bid: number;
  ask: number;
  spread: number;
  spread_pips: number;
  time: number;
  is_stale: boolean;
}

export interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorValues {
  time: number;
  ema_fast?: number | null;
  ema_slow?: number | null;
  rsi?: number | null;
  atr?: number | null;
  bb_upper?: number | null;
  bb_middle?: number | null;
  bb_lower?: number | null;
  support_level?: number | null;
  resistance_level?: number | null;
  regime: string;
}

export interface MarketOverview {
  symbol: string;
  ticker: TickerData;
  indicators: IndicatorValues;
  candles: CandleData[];
}

export interface AiDecisionOutput {
  symbol: string;
  decision: "BUY" | "SELL" | "WAIT";
  market_regime: "trending" | "ranging" | "high_volatility" | "uncertain";
  strategy?: string | null;
  confidence?: number | null;
  trade_expectancy?: number | null;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  invalidation_conditions: string[];
  reasoning_summary: string;
  feature_timestamp?: string | null;
  model_version?: string | null;
}

export interface Position {
  ticket: number;
  symbol: string;
  position_type: "BUY" | "SELL";
  volume: number;
  open_price: number;
  current_price: number;
  sl: number;
  tp: number;
  swap: number;
  commission: number;
  profit: number;
  open_time: string;
  status: string;
  strategy_used?: string | null;
  signal_id?: string | null;
}

export interface Order {
  client_order_id: string;
  broker_order_id?: number | null;
  timestamp: string;
  symbol: string;
  order_type: string;
  volume: number;
  requested_price: number;
  executed_price?: number | null;
  sl: number;
  tp: number;
  status: string;
  retcode?: number | null;
  broker_comment?: string | null;
}

export interface Trade {
  id: number;
  ticket: number;
  symbol: string;
  trade_type: "BUY" | "SELL";
  volume: number;
  open_price: number;
  close_price: number;
  sl: number;
  tp: number;
  open_time: string;
  close_time: string;
  gross_pnl: number;
  net_pnl: number;
  commission: number;
  swap: number;
  slippage: number;
  exit_reason: string;
  strategy_used: string;
  model_version: string;
  market_regime: string;
}

export interface BotState {
  current_state: string;
  previous_state?: string | null;
  last_transition_time: string;
  transition_reason: string;
  error_message?: string | null;
  can_enter_trades: boolean;
  can_monitor_positions: boolean;
  is_evaluating: boolean;
  mt5_connected: boolean;
  is_demo_account: boolean;
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  mode: string;
  live_trading_enabled: boolean;
  mt5_connected: boolean;
  bot_state: string;
  version?: string;
}

export interface MT5StatusInfo {
  connected: boolean;
  terminal_info?: {
    connected: boolean;
    trade_allowed: boolean;
    name?: string;
    path?: string;
    company?: string;
  } | null;
  account_info?: {
    login: number;
    trade_mode: number;
    balance: number;
    equity: number;
    profit: number;
    server: string;
    currency: string;
    company: string;
  } | null;
  is_demo: boolean;
  is_live_blocked: boolean;
}

export interface MT5AccountInfo {
  login: number;
  trade_mode: number;
  trade_mode_desc: string;
  is_demo: boolean;
  balance: number;
  equity: number;
  profit: number;
  margin: number;
  margin_free: number;
  margin_level: number;
  currency: string;
  server: string;
  company: string;
  leverage: number;
}

export interface AppSettings {
  trading_mode: string;
  live_trading_enabled: boolean;
  allowed_symbols: string[];
  max_risk_per_trade_pct: number;
  max_total_open_risk_pct: number;
  max_daily_loss_pct: number;
  max_weekly_loss_pct: number;
  max_consecutive_losses: number;
  max_trades_per_day: number;
  max_spread_pips: number;
  strategy_mode: string;
  decision_interval_seconds: number;
  symbol_mapping: Record<string, string>;
}

export interface RiskStatus {
  max_risk_per_trade_pct: number;
  max_total_open_risk_pct: number;
  current_open_risk_pct: number;
  daily_loss_pct: number;
  max_daily_loss_pct: number;
  weekly_loss_pct: number;
  max_weekly_loss_pct: number;
  consecutive_losses: number;
  max_consecutive_losses: number;
  trades_today: number;
  max_trades_per_day: number;
  is_locked: boolean;
  lock_reason?: string | null;
  account_equity: number;
  account_balance: number;
  free_margin: number;
  spread_pips: number;
  max_spread_pips: number;
  can_trade: boolean;
  rejection_reasons: string[];
}

export interface PerformanceMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  gross_profit: number;
  gross_loss: number;
  net_pnl: number;
  total_commission: number;
  total_swap: number;
  average_win: number;
  average_loss: number;
  trade_expectancy: number;
  max_drawdown_amount: number;
  max_drawdown_pct: number;
  performance_by_strategy: Record<string, any>;
  performance_by_regime: Record<string, any>;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  balance: number;
  drawdown_pct: number;
}

export interface ReportSummary {
  period_type: string;
  period_start: string;
  period_end: string;
  timezone: string;
  starting_balance: number;
  ending_balance: number;
  starting_equity: number;
  ending_equity: number;
  metrics: PerformanceMetrics;
  equity_curve: EquityPoint[];
  trades: any[];
  data_limitations: string[];
}

export interface BacktestResult {
  symbol: string;
  strategy_mode: string;
  initial_balance: number;
  final_balance: number;
  net_pnl: number;
  return_pct: number;
  metrics: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    profit_factor: number;
    gross_profit: number;
    gross_loss: number;
    average_win: number;
    average_loss: number;
    trade_expectancy: number;
    max_drawdown_pct: number;
  };
  equity_curve: Array<{
    time: number;
    balance: number;
    equity: number;
    drawdown_pct: number;
  }>;
  trades: any[];
  data_limitations: string[];
}

export interface AuditEvent {
  id: number;
  timestamp: string;
  event_type: string;
  severity: "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  message: string;
  metadata?: any;
}
