"use client";

import React from "react";
import { ShieldAlert, Info } from "lucide-react";

export function CopilotSafetyBanner() {
  return (
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-300 flex items-start gap-2.5">
      <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
      <div className="space-y-1">
        <p className="font-semibold text-amber-200">
          Assistive Clinical Decision Support (CDSS Level 1 & 2)
        </p>
        <p className="text-amber-300/90 leading-relaxed">
          NIDAN AI assists licensed medical practitioners by surfacing evidence-grounded laboratory trajectories,
          medication records, and safety observations. It does not provide autonomous diagnoses, treatment plans, or prescriptions.
          Human clinical review is mandatory.
        </p>
      </div>
    </div>
  );
}
