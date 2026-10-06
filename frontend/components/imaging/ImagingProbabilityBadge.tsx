"use client";

import React from "react";

interface ImagingProbabilityBadgeProps {
  probability: number;
  threshold: number;
  confidence?: number;
  status?: string;
  size?: "sm" | "md" | "lg";
}

export const ImagingProbabilityBadge: React.FC<ImagingProbabilityBadgeProps> = ({
  probability,
  threshold,
  confidence,
  status,
  size = "md",
}) => {
  const pct = Math.round(probability * 100);
  const threshPct = Math.round(threshold * 100);

  const isUncertain = status === "UNCERTAIN" || Math.abs(probability - threshold) <= 0.06;
  const isAbove = probability >= threshold;

  let badgeStyle = "bg-slate-800/80 text-slate-300 border-slate-700/60";
  let labelText = "Below Threshold";

  if (isUncertain) {
    badgeStyle = "bg-amber-950/60 text-amber-300 border-amber-500/40";
    labelText = "Borderline / Uncertain";
  } else if (isAbove) {
    badgeStyle = "bg-indigo-950/70 text-indigo-300 border-indigo-500/40 shadow-sm shadow-indigo-950/40";
    labelText = "Above Model Threshold";
  }

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs gap-1.5",
    md: "px-2.5 py-1 text-xs md:text-sm gap-2",
    lg: "px-3.5 py-1.5 text-sm md:text-base gap-2.5",
  };

  return (
    <div
      className={`inline-flex items-center rounded-lg border font-mono font-medium ${badgeStyle} ${sizeClasses[size]}`}
      title={`Model Probability: ${pct}% | Decision Threshold: ${threshPct}% | Confidence: ${Math.round((confidence || 1) * 100)}%`}
    >
      <span className="font-semibold">{pct}%</span>
      <span className="text-[10px] opacity-75 font-sans uppercase tracking-wider">
        (Thr: {threshPct}%)
      </span>
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
      <span className="text-[11px] font-sans font-normal hidden sm:inline-block">
        {labelText}
      </span>
    </div>
  );
};
