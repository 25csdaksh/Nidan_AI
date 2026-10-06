"use client";

import React from "react";
import { ImagingTimelineItem } from "@/lib/types";

interface ImagingTimelineProps {
  timeline: ImagingTimelineItem[];
  onSelectStudy: (studyId: string) => void;
}

export const ImagingTimeline: React.FC<ImagingTimelineProps> = ({
  timeline,
  onSelectStudy,
}) => {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800">
        No historical imaging studies recorded for this patient.
      </div>
    );
  }

  return (
    <div className="relative border-l-2 border-slate-800 pl-6 space-y-6 my-4">
      {timeline.map((item, idx) => {
        const dateStr = item.study_date ? new Date(item.study_date).toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
        }) : "Date Unspecified";

        return (
          <div key={item.study_id} className="relative group">
            {/* Timeline Bullet */}
            <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-indigo-600 border-4 border-slate-950 group-hover:scale-125 transition-transform" />

            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-indigo-500/50 transition">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-100 text-sm">{dateStr}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
                    {item.modality} · {item.body_part} ({item.view_position || "PA"})
                  </span>
                </div>
                <button
                  onClick={() => onSelectStudy(item.study_id)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                >
                  Inspect Study →
                </button>
              </div>

              {/* Key Findings Summary */}
              {item.key_findings && item.key_findings.length > 0 ? (
                <div className="mt-3 space-y-1.5">
                  <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">
                    Model Findings Above Threshold:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {item.key_findings.map((kf, kIdx) => (
                      <div
                        key={kIdx}
                        className="px-2.5 py-1 rounded-lg bg-slate-950 text-xs border border-slate-800 flex items-center gap-2"
                      >
                        <span className="text-slate-200">{kf.finding_name}</span>
                        <span className="font-mono text-amber-400 font-semibold">{Math.round(kf.probability * 100)}%</span>
                        <span className="text-[10px] font-mono px-1 rounded bg-slate-800 text-slate-400">
                          {kf.review_status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500 mt-2 italic">
                  All radiographic patterns remained below configured decision thresholds.
                </p>
              )}

              {/* Review summary count */}
              <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center gap-3 text-[11px] text-slate-400 font-mono">
                <span>Total Findings: {item.findings_count}</span>
                <span>Verified: {item.review_status_summary?.ACCEPTED || 0}</span>
                <span>Pending Review: {item.review_status_summary?.PENDING || 0}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
