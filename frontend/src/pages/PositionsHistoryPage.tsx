import React, { useState } from "react";
import {
  ListOrdered,
  Layers,
  Archive,
  FileText,
  AlertTriangle,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Position, Trade, Order } from "../types";
import { StatusBadge } from "../components/StatusBadge";
import { ConfirmModal } from "../components/ConfirmModal";

interface PositionsHistoryPageProps {
  positions: Position[];
  trades: Trade[];
  orders: Order[];
  onRefresh: () => Promise<void>;
  onClosePosition: (ticket: number) => Promise<void>;
  onEmergencyFlatten: () => Promise<void>;
}

export const PositionsHistoryPage: React.FC<PositionsHistoryPageProps> = ({
  positions,
  trades,
  orders,
  onRefresh,
  onClosePosition,
  onEmergencyFlatten,
}) => {
  const [activeTab, setActiveTab] = useState<"positions" | "trades" | "orders">("positions");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [showFlattenModal, setShowFlattenModal] = useState<boolean>(false);
  const [closingTicket, setClosingTicket] = useState<number | null>(null);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
    }
  };

  // Trade metrics summary
  const totalClosed = trades.length;
  const winningTrades = trades.filter((t) => t.net_pnl > 0).length;
  const winRate = totalClosed > 0 ? (winningTrades / totalClosed) * 100 : 0;
  const totalNetPnL = trades.reduce((acc, t) => acc + t.net_pnl, 0);

  // Filtered lists
  const filteredPositions = positions.filter(
    (p) =>
      p.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.ticket.toString().includes(searchTerm)
  );

  const filteredTrades = trades.filter(
    (t) =>
      t.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.ticket.toString().includes(searchTerm) ||
      t.strategy_used.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredOrders = orders.filter(
    (o) =>
      o.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      o.client_order_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (o.broker_order_id && o.broker_order_id.toString().includes(searchTerm))
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Top Header & Tab Controls */}
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
        {/* Navigation Tabs */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <button
            onClick={() => setActiveTab("positions")}
            className="btn"
            style={{
              background: activeTab === "positions" ? "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)" : "transparent",
              color: activeTab === "positions" ? "#fff" : "var(--text-secondary)",
              border: activeTab === "positions" ? "none" : "1px solid var(--border-subtle)",
              padding: "0.5rem 1rem",
              fontSize: "0.85rem",
            }}
          >
            <Layers size={16} />
            <span>Open Positions ({positions.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("trades")}
            className="btn"
            style={{
              background: activeTab === "trades" ? "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)" : "transparent",
              color: activeTab === "trades" ? "#fff" : "var(--text-secondary)",
              border: activeTab === "trades" ? "none" : "1px solid var(--border-subtle)",
              padding: "0.5rem 1rem",
              fontSize: "0.85rem",
            }}
          >
            <Archive size={16} />
            <span>Closed Trades ({trades.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("orders")}
            className="btn"
            style={{
              background: activeTab === "orders" ? "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)" : "transparent",
              color: activeTab === "orders" ? "#fff" : "var(--text-secondary)",
              border: activeTab === "orders" ? "none" : "1px solid var(--border-subtle)",
              padding: "0.5rem 1rem",
              fontSize: "0.85rem",
            }}
          >
            <FileText size={16} />
            <span>Order Audit Log ({orders.length})</span>
          </button>
        </div>

        {/* Search & Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ position: "relative", width: "200px" }}>
            <Search
              size={14}
              color="var(--text-muted)"
              style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }}
            />
            <input
              type="text"
              placeholder="Search ticket / symbol..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              style={{ paddingLeft: "30px", fontSize: "0.8rem", padding: "0.45rem 0.65rem 0.45rem 2rem" }}
            />
          </div>

          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="btn btn-secondary"
            title="Refresh positions"
            style={{ padding: "0.45rem 0.75rem" }}
          >
            <RefreshCw size={14} className={isRefreshing ? "spin" : ""} />
          </button>

          {activeTab === "positions" && positions.length > 0 && (
            <button
              onClick={() => setShowFlattenModal(true)}
              className="btn btn-danger"
              style={{ padding: "0.45rem 0.85rem", fontSize: "0.8rem" }}
            >
              <AlertTriangle size={14} />
              <span>Emergency Flatten All</span>
            </button>
          )}
        </div>
      </div>

      {/* Tab 1: Open Positions */}
      {activeTab === "positions" && (
        <div className="glass-panel" style={{ padding: "1.25rem" }}>
          {filteredPositions.length > 0 ? (
            <div style={{ overflowX: "auto" }}>
              <table className="fintech-table">
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Volume</th>
                    <th>Open Price</th>
                    <th>Current Price</th>
                    <th>SL</th>
                    <th>TP</th>
                    <th>Swap</th>
                    <th>Comm.</th>
                    <th>Floating PnL</th>
                    <th>Open Time</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPositions.map((p) => {
                    const isProfit = p.profit >= 0;
                    return (
                      <tr key={p.ticket}>
                        <td className="tabular-nums" style={{ fontWeight: 600 }}>
                          #{p.ticket}
                        </td>
                        <td style={{ fontWeight: 700 }}>{p.symbol}</td>
                        <td>
                          <StatusBadge type="position_type" value={p.position_type} size="sm" />
                        </td>
                        <td className="tabular-nums">{p.volume.toFixed(2)}</td>
                        <td className="tabular-nums">{p.open_price.toFixed(5)}</td>
                        <td className="tabular-nums">{p.current_price.toFixed(5)}</td>
                        <td className="tabular-nums" style={{ color: "#f87171" }}>
                          {p.sl.toFixed(5)}
                        </td>
                        <td className="tabular-nums" style={{ color: "#34d399" }}>
                          {p.tp.toFixed(5)}
                        </td>
                        <td className="tabular-nums">${p.swap.toFixed(2)}</td>
                        <td className="tabular-nums">${p.commission.toFixed(2)}</td>
                        <td
                          className="tabular-nums"
                          style={{
                            fontWeight: 700,
                            color: isProfit ? "var(--color-bullish)" : "var(--color-bearish)",
                          }}
                        >
                          {isProfit ? "+" : ""}${p.profit.toFixed(2)}
                        </td>
                        <td className="tabular-nums" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          {p.open_time ? p.open_time.substring(11, 19) : "N/A"}
                        </td>
                        <td>
                          <button
                            onClick={() => setClosingTicket(p.ticket)}
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
            <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
              No open positions. TradePilot AI executes eligible orders automatically when risk and strategy rules are satisfied.
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Closed Trades */}
      {activeTab === "trades" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* Quick Metrics Banner */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "1rem",
            }}
          >
            <div className="glass-panel" style={{ padding: "1rem" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Total Net Realized PnL</div>
              <div
                className="tabular-nums"
                style={{
                  fontSize: "1.3rem",
                  fontWeight: 700,
                  color: totalNetPnL >= 0 ? "var(--color-bullish)" : "var(--color-bearish)",
                }}
              >
                {totalNetPnL >= 0 ? "+" : ""}${totalNetPnL.toFixed(2)}
              </div>
            </div>

            <div className="glass-panel" style={{ padding: "1rem" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Win Rate</div>
              <div className="tabular-nums" style={{ fontSize: "1.3rem", fontWeight: 700, color: "#38bdf8" }}>
                {winRate.toFixed(1)}% ({winningTrades}/{totalClosed})
              </div>
            </div>

            <div className="glass-panel" style={{ padding: "1rem" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Total Closed Trades</div>
              <div className="tabular-nums" style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {totalClosed}
              </div>
            </div>
          </div>

          <div className="glass-panel" style={{ padding: "1.25rem" }}>
            {filteredTrades.length > 0 ? (
              <div style={{ overflowX: "auto" }}>
                <table className="fintech-table">
                  <thead>
                    <tr>
                      <th>Ticket</th>
                      <th>Symbol</th>
                      <th>Type</th>
                      <th>Volume</th>
                      <th>Open Price</th>
                      <th>Close Price</th>
                      <th>Net PnL</th>
                      <th>Comm.</th>
                      <th>Exit Reason</th>
                      <th>Strategy</th>
                      <th>Regime</th>
                      <th>Close Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTrades.map((t) => {
                      const isProfit = t.net_pnl >= 0;
                      return (
                        <tr key={t.id || t.ticket}>
                          <td className="tabular-nums">#{t.ticket}</td>
                          <td style={{ fontWeight: 600 }}>{t.symbol}</td>
                          <td>
                            <StatusBadge type="position_type" value={t.trade_type} size="sm" />
                          </td>
                          <td className="tabular-nums">{t.volume.toFixed(2)}</td>
                          <td className="tabular-nums">{t.open_price.toFixed(5)}</td>
                          <td className="tabular-nums">{t.close_price.toFixed(5)}</td>
                          <td
                            className="tabular-nums"
                            style={{
                              fontWeight: 700,
                              color: isProfit ? "var(--color-bullish)" : "var(--color-bearish)",
                            }}
                          >
                            {isProfit ? "+" : ""}${t.net_pnl.toFixed(2)}
                          </td>
                          <td className="tabular-nums">${t.commission.toFixed(2)}</td>
                          <td style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                            {t.exit_reason || "Normal exit"}
                          </td>
                          <td style={{ fontSize: "0.75rem", color: "#c084fc" }}>
                            {t.strategy_used || "Standard"}
                          </td>
                          <td>
                            <StatusBadge type="regime" value={t.market_regime} size="sm" />
                          </td>
                          <td className="tabular-nums" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                            {t.close_time ? t.close_time.substring(11, 19) : "N/A"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                No closed trades recorded in the database yet.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Order Audit Log */}
      {activeTab === "orders" && (
        <div className="glass-panel" style={{ padding: "1.25rem" }}>
          {filteredOrders.length > 0 ? (
            <div style={{ overflowX: "auto" }}>
              <table className="fintech-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Client Order ID</th>
                    <th>Broker Order #</th>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Volume</th>
                    <th>Req Price</th>
                    <th>Exec Price</th>
                    <th>SL / TP</th>
                    <th>Status</th>
                    <th>Broker Note</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map((o) => (
                    <tr key={o.client_order_id}>
                      <td className="tabular-nums" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {o.timestamp ? o.timestamp.substring(11, 19) : "N/A"}
                      </td>
                      <td style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        {o.client_order_id.substring(0, 14)}...
                      </td>
                      <td className="tabular-nums">
                        {o.broker_order_id ? `#${o.broker_order_id}` : "-"}
                      </td>
                      <td style={{ fontWeight: 600 }}>{o.symbol}</td>
                      <td>
                        <StatusBadge type="position_type" value={o.order_type} size="sm" />
                      </td>
                      <td className="tabular-nums">{o.volume.toFixed(2)}</td>
                      <td className="tabular-nums">{o.requested_price.toFixed(5)}</td>
                      <td className="tabular-nums">{o.executed_price ? o.executed_price.toFixed(5) : "-"}</td>
                      <td className="tabular-nums" style={{ fontSize: "0.75rem" }}>
                        {o.sl.toFixed(5)} / {o.tp.toFixed(5)}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            o.status === "FILLED"
                              ? "badge-bullish"
                              : o.status === "REJECTED"
                              ? "badge-bearish"
                              : "badge-neutral"
                          }`}
                          style={{ fontSize: "0.7rem" }}
                        >
                          {o.status}
                        </span>
                      </td>
                      <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {o.broker_comment || "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
              No order audit logs recorded yet.
            </div>
          )}
        </div>
      )}

      {/* Confirmation Modals */}
      <ConfirmModal
        isOpen={showFlattenModal}
        title="Emergency Flatten All Positions"
        message="This will immediately send market orders to close ALL currently open positions on the MT5 terminal. Use only in emergency or risk liquidation scenarios."
        confirmText="Flatten All Positions"
        isDangerous={true}
        onConfirm={async () => {
          setShowFlattenModal(false);
          await onEmergencyFlatten();
        }}
        onCancel={() => setShowFlattenModal(false)}
      />

      <ConfirmModal
        isOpen={closingTicket !== null}
        title={`Close Position #${closingTicket}`}
        message={`Are you sure you want to close position #${closingTicket} at market price?`}
        confirmText="Close Position"
        isDangerous={true}
        onConfirm={async () => {
          if (closingTicket !== null) {
            const ticket = closingTicket;
            setClosingTicket(null);
            await onClosePosition(ticket);
          }
        }}
        onCancel={() => setClosingTicket(null)}
      />
    </div>
  );
};
