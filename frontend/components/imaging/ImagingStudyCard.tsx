"use client";

import React from "react";
import { ImagingStudy } from "@/lib/types";

interface ImagingStudyCardProps {
  study: ImagingStudy;
  isSelected?: boolean;
  onSelect: (study: ImagingStudy) => void;
}

export const ImagingStudyCard: React.FC<ImagingStudyCardProps> = ({
  study,
  isSelected = false,
  onSelect,
}) => {
  const dateStr = study.study_date ? new Date(study.study_date).toLocaleDateString() : "Unknown Date";

  const qualityColor = {
    QUALITY_ACCEPTED: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    QUALITY_WARNING: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    QUALITY_REJECTED: "bg-rose-500/10 text-rose-300 border-rose-500/30",
  }[study.image_quality_status] || "bg-slate-800 text-slate-300";

  return (
    <div
      onClick={() => onSelect(study)}
      className={`p-4 rounded-xl border cursor-pointer transition-all duration-150 ${
        isSelected
          ? "bg-indigo-950/40 border-indigo-500/80 shadow-lg shadow-indigo-950/30"
          : "bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/60 hover:border-slate-700"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-xs px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
              {study.modality}
            </span>
            <span className="font-semibold text-slate-100 text-sm">{study.body_part} ({study.view_position || "PA"})</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Study Date: {dateStr}</p>
        </div>

        {/* Quality status badge */}
        <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${qualityColor}`}>
          {study.image_quality_status.replace("QUALITY_", "")}
        </span>
      </div>

      <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
        <span>Status: <span className="text-slate-200">{study.processing_status}</span></span>
        <span className="text-indigo-400 font-sans hover:underline">Select Study →</span>
      </div>
    </div>
  );
};
