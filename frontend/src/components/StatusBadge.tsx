import React from "react";
import { CheckCircle2, AlertTriangle, XCircle, Clock, ShieldCheck, ShieldAlert } from "lucide-react";

interface StatusBadgeProps {
  type: "decision" | "regime" | "bot_state" | "position_type" | "risk" | "severity";
  value: string;
  size?: "sm" | "md";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, value, size = "md" }) => {
  const val = (value || "").toUpperCase();

  const getStyleAndIcon = () => {
    switch (type) {
      case "decision":
        if (val === "BUY") {
          return {
            className: "badge-bullish",
            icon: <CheckCircle2 size={13} />,
            label: "BUY",
          };
        }
        if (val === "SELL") {
          return {
            className: "badge-bearish",
            icon: <XCircle size={13} />,
            label: "SELL",
          };
        }
        return {
          className: "badge-neutral",
          icon: <Clock size={13} />,
          label: "WAIT",
        };

      case "regime":
        if (val.includes("TREND")) {
          return {
            className: "badge-bullish",
            label: "TRENDING",
          };
        }
        if (val.includes("RANGE")) {
          return {
            className: "badge-demo",
            label: "RANGING",
          };
        }
        if (val.includes("VOLATIL")) {
          return {
            className: "badge-bearish",
            label: "HIGH VOLATILITY",
          };
        }
        return {
          className: "badge-neutral",
          label: "UNCERTAIN",
        };

      case "bot_state":
        if (val === "RUNNING") {
          return {
            className: "badge-bullish",
            icon: <span className="pulse-dot pulse-dot-green" />,
            label: "RUNNING",
          };
        }
        if (val === "PAUSED") {
          return {
            className: "badge-neutral",
            icon: <span className="pulse-dot pulse-dot-amber" />,
            label: "PAUSED",
          };
        }
        if (val === "ERROR" || val === "SAFE_STOP") {
          return {
            className: "badge-bearish",
            icon: <span className="pulse-dot pulse-dot-red" />,
            label: val,
          };
        }
        return {
          className: "badge-demo",
          label: val || "IDLE",
        };

      case "position_type":
        return val === "BUY"
          ? { className: "badge-bullish", label: "BUY" }
          : { className: "badge-bearish", label: "SELL" };

      case "risk":
        return val === "LOCKED"
          ? {
              className: "badge-bearish",
              icon: <ShieldAlert size={13} />,
              label: "RISK LOCKED",
            }
          : {
              className: "badge-bullish",
              icon: <ShieldCheck size={13} />,
              label: "SAFE",
            };

      case "severity":
        if (val === "CRITICAL" || val === "ERROR") {
          return { className: "badge-bearish", icon: <AlertTriangle size={13} />, label: val };
        }
        if (val === "WARNING") {
          return { className: "badge-neutral", icon: <AlertTriangle size={13} />, label: val };
        }
        return { className: "badge-demo", label: val };

      default:
        return { className: "badge-demo", label: val };
    }
  };

  const { className, icon, label } = getStyleAndIcon();
  const fontSize = size === "sm" ? "0.7rem" : "0.75rem";

  return (
    <span className={`badge ${className}`} style={{ fontSize }}>
      {icon}
      <span>{label}</span>
    </span>
  );
};
