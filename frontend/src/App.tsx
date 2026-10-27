import React, { useState, useEffect, useCallback } from "react";
import {
  BotState,
  HealthStatus,
  MT5StatusInfo,
  RiskStatus,
  MarketOverview,
  CandleData,
  IndicatorValues,
  TickerData,
  AiDecisionOutput,
  Position,
  Trade,
  Order,
  AuditEvent,
} from "./types";
import { api } from "./services/api";
import { Navbar } from "./components/Navbar";
import { Sidebar, NavPage } from "./components/Sidebar";

// 7 Core Pages
import { OverviewDashboard } from "./pages/OverviewDashboard";
import { TradingTerminal } from "./pages/TradingTerminal";
import { AiAnalysisPage } from "./pages/AiAnalysisPage";
import { PositionsHistoryPage } from "./pages/PositionsHistoryPage";
import { RiskManagementPage } from "./pages/RiskManagementPage";
import { ReportsAnalyticsPage } from "./pages/ReportsAnalyticsPage";
import { SettingsHealthPage } from "./pages/SettingsHealthPage";

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<NavPage>("overview");
  const [timeframe, setTimeframe] = useState<string>("M15");

  // Core Data States
  const [botState, setBotState] = useState<BotState | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [mt5Status, setMt5Status] = useState<MT5StatusInfo | null>(null);
  const [riskStatus, setRiskStatus] = useState<RiskStatus | null>(null);

  // Market & Analysis
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null);
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [indicators, setIndicators] = useState<IndicatorValues | null>(null);
  const [ticker, setTicker] = useState<TickerData | null>(null);
  const [latestAnalysis, setLatestAnalysis] = useState<AiDecisionOutput | null>(null);
  const [analysisHistory, setAnalysisHistory] = useState<AiDecisionOutput[]>([]);

  // Positions & Trades
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);

  // Initial Data Fetch & Periodic Polling
  const pollFastData = useCallback(async () => {
    try {
      const [bState, rStatus, mOverview, pos] = await Promise.all([
        api.getBotState().catch(() => null),
        api.getRiskStatus().catch(() => null),
        api.getMarketOverview("EURUSD", timeframe).catch(() => null),
        api.getPositions().catch(() => []),
      ]);

      if (bState) setBotState(bState);
      if (rStatus) setRiskStatus(rStatus);
      if (pos) setPositions(pos);

      if (mOverview) {
        setMarketOverview(mOverview);
        if (mOverview.ticker) setTicker(mOverview.ticker);
        if (mOverview.indicators) setIndicators(mOverview.indicators);
        if (mOverview.candles && mOverview.candles.length > 0) {
          setCandles(mOverview.candles);
        }
      }
    } catch (err) {
      console.warn("Poll error:", err);
    }
  }, [timeframe]);

  const pollSlowData = useCallback(async () => {
    try {
      const [mt5, hlth, aiLatest, aiHist, trd, ord, aud] = await Promise.all([
        api.getMt5Status().catch(() => null),
        api.getHealth().catch(() => null),
        api.getLatestAnalysis("EURUSD").catch(() => null),
        api.getAnalysisHistory("EURUSD", 20).catch(() => []),
        api.getTrades(50).catch(() => []),
        api.getOrders(50).catch(() => []),
        api.getAuditLog(50).catch(() => []),
      ]);

      if (mt5) setMt5Status(mt5);
      if (hlth) setHealth(hlth);
      if (aiLatest) setLatestAnalysis(aiLatest);
      if (aiHist) setAnalysisHistory(aiHist);
      if (trd) setTrades(trd);
      if (ord) setOrders(ord);
      if (aud) setAuditEvents(aud);
    } catch (err) {
      console.warn("Slow poll error:", err);
    }
  }, []);

  // Set up intervals
  useEffect(() => {
    pollFastData();
    pollSlowData();

    // Fast poll: market overview, ticker, bot state, positions every 3 seconds
    const fastInterval = setInterval(pollFastData, 3000);
    // Slow poll: history, audit logs, mt5 details every 10 seconds
    const slowInterval = setInterval(pollSlowData, 10000);

    return () => {
      clearInterval(fastInterval);
      clearInterval(slowInterval);
    };
  }, [pollFastData, pollSlowData]);

  // Action Handlers
  const handleReconnectMt5 = async () => {
    await api.reconnectMt5();
    await pollSlowData();
    await pollFastData();
  };

  const handleStartBot = async () => {
    await api.startBot();
    await pollFastData();
  };

  const handlePauseBot = async () => {
    await api.pauseBot();
    await pollFastData();
  };

  const handleResumeBot = async () => {
    await api.resumeBot();
    await pollFastData();
  };

  const handleStopBot = async () => {
    await api.stopBot();
    await pollFastData();
  };

  const handleClosePosition = async (ticket: number) => {
    await api.closePosition(ticket, "Closed manually via TradePilot UI");
    await pollFastData();
  };

  const handleEmergencyFlatten = async () => {
    await api.emergencyFlatten("Emergency manual liquidation from TradePilot UI");
    await pollFastData();
  };

  const handleResetRiskLock = async () => {
    await api.resetRiskLock();
    await pollFastData();
  };

  const handleTriggerEvaluation = async () => {
    const analysis = await api.evaluateAnalysis("EURUSD");
    setLatestAnalysis(analysis);
    await pollSlowData();
  };

  const handleTimeframeChange = async (newTf: string) => {
    setTimeframe(newTf);
    try {
      const newCandles = await api.getCandles("EURUSD", newTf, 100);
      setCandles(newCandles);
      const newIndicators = await api.getIndicators("EURUSD", newTf);
      setIndicators(newIndicators);
    } catch (err) {
      console.warn("Error changing timeframe:", err);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Sidebar
        currentPage={currentPage}
        onSelectPage={setCurrentPage}
        riskStatus={riskStatus}
      />

      {/* Main View Area */}
      <div className="main-content">
        <Navbar
          botState={botState}
          health={health}
          mt5Status={mt5Status}
          riskStatus={riskStatus}
          onReconnectMt5={handleReconnectMt5}
        />

        <main className="page-body">
          {currentPage === "overview" && (
            <OverviewDashboard
              botState={botState}
              riskStatus={riskStatus}
              marketOverview={marketOverview}
              latestAnalysis={latestAnalysis}
              positions={positions}
              auditEvents={auditEvents}
              onNavigate={setCurrentPage}
              onClosePosition={handleClosePosition}
            />
          )}

          {currentPage === "terminal" && (
            <TradingTerminal
              marketOverview={marketOverview}
              candles={candles}
              indicators={indicators}
              ticker={ticker}
              positions={positions}
              timeframe={timeframe}
              onTimeframeChange={handleTimeframeChange}
              onClosePosition={handleClosePosition}
            />
          )}

          {currentPage === "analysis" && (
            <AiAnalysisPage
              latestAnalysis={latestAnalysis}
              history={analysisHistory}
              onTriggerEvaluation={handleTriggerEvaluation}
            />
          )}

          {currentPage === "positions" && (
            <PositionsHistoryPage
              positions={positions}
              trades={trades}
              orders={orders}
              onRefresh={pollFastData}
              onClosePosition={handleClosePosition}
              onEmergencyFlatten={handleEmergencyFlatten}
            />
          )}

          {currentPage === "risk" && (
            <RiskManagementPage
              riskStatus={riskStatus}
              onResetRiskLock={handleResetRiskLock}
              onRefresh={pollFastData}
            />
          )}

          {currentPage === "reports" && <ReportsAnalyticsPage />}

          {currentPage === "settings" && (
            <SettingsHealthPage
              botState={botState}
              mt5Status={mt5Status}
              onStartBot={handleStartBot}
              onPauseBot={handlePauseBot}
              onResumeBot={handleResumeBot}
              onStopBot={handleStopBot}
              onEmergencyFlatten={handleEmergencyFlatten}
              onReconnectMt5={handleReconnectMt5}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
