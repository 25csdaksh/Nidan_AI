"use client";

import React, { useState } from "react";
import { AlertTriangle, ShieldCheck, X } from "lucide-react";

export function DisclaimerBanner() {
  const [acknowledged, setAcknowledged] = useState(false);

  if (acknowledged) {
    return (
      <div className="bg-emerald-950/40 border-b border-emerald-800/40 px-4 py-1.5 text-xs text-emerald-300 flex items-center justify-between">
        <div className="flex items-center gap-2 max-w-7xl mx-auto w-full">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span>
            <strong>CDSS Mode Active:</strong> NIDAN AI provides assistive clinical insights for licensed medical professionals. Human-in-the-loop review mandatory.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-amber-950/70 border-b border-amber-600/40 px-4 py-2.5 text-xs text-amber-200 shadow-sm transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 animate-pulse" />
          <div>
            <span className="font-semibold text-amber-300">CLINICAL NOTICE:</span>{" "}
            <span>
              NIDAN AI is an assistive decision-support platform, <strong>NOT</strong> a doctor replacement. It must never independently provide a definitive medical diagnosis, prescription, or treatment decision.
            </span>
          </div>
        </div>
        <button
          onClick={() => setAcknowledged(true)}
          className="shrink-0 bg-amber-600/30 hover:bg-amber-600/50 text-amber-100 px-2.5 py-1 rounded text-[11px] font-medium transition border border-amber-500/40"
        >
          Acknowledge CDSS Policy
        </button>
      </div>
    </div>
  );
}
