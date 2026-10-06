"use client";

import React from "react";

interface ImagingSafetyBannerProps {
  customMessage?: string;
}

export const ImagingSafetyBanner: React.FC<ImagingSafetyBannerProps> = ({ customMessage }) => {
  return (
    <div className="bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 my-4 flex items-start gap-3 shadow-lg shadow-amber-950/20 text-amber-200">
      <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 shrink-0 mt-0.5">
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <div className="text-xs md:text-sm leading-relaxed">
        <p className="font-semibold text-amber-300 mb-1 flex items-center gap-2">
          CLINICAL DECISION SUPPORT SYSTEM (CDSS) — ASSISTIVE ONLY
          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">
            NON-AUTONOMOUS
          </span>
        </p>
        <p className="text-amber-200/90">
          {customMessage ||
            "Medical imaging outputs, neural probability scores, and localization heatmaps are algorithmic assistive evidence. They are NOT confirmed radiological diagnoses and DO NOT replace physician/radiologist clinical evaluation. Mandatory human clinician review is required before clinical action."}
        </p>
      </div>
    </div>
  );
};
