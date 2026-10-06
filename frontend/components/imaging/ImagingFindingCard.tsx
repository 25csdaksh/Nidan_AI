"use client";

import React from "react";
import { ImagingFinding } from "@/lib/types";
import { ImagingProbabilityBadge } from "./ImagingProbabilityBadge";

interface ImagingFindingCardProps {
  finding: ImagingFinding;
  onViewLocalization: (finding: ImagingFinding) => void;
  onViewEvidence: (finding: ImagingFinding) => void;
  onOpenReview: (finding: ImagingFinding) => void;
}

export const ImagingFindingCard: React.FC<ImagingFindingCardProps> = ({
  finding,
  onViewLocalization,
  onViewEvidence,
  onOpenReview,
}) => {
  const isAbove = finding.probability >= finding.model_threshold;

  const reviewBadgeStyles = {
    PENDING: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    ACCEPTED: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 font-semibold",
    MODIFIED: "bg-sky-500/15 text-sky-300 border-sky-500/40",
    REJECTED: "bg-rose-500/15 text-rose-300 border-rose-500/40",
  };

  return (
    <div className={`p-4 rounded-xl border transition-all duration-200 ${
      isAbove
        ? "bg-slate-900/90 border-slate-700/80 shadow-md shadow-indigo-950/20"
        : "bg-slate-900/50 border-slate-800/60 opacity-80 hover:opacity-100"
    }`}>
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-slate-100 text-sm md:text-base">
              {finding.finding_name}
            </h4>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              {finding.anatomical_region}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-0.5">Code: {finding.finding_code}</p>
        </div>

        {/* Review Status */}
        <div className="flex items-center gap-2">
          <span className={`px-2.5 py-1 rounded-full text-xs font-mono border ${reviewBadgeStyles[finding.review_status] || "bg-slate-800 text-slate-300"}`}>
            Review: {finding.review_status}
          </span>
        </div>
      </div>

      {/* Probability & Calibration Row */}
      <div className="my-3 flex flex-wrap items-center gap-3">
        <ImagingProbabilityBadge
          probability={finding.probability}
          threshold={finding.model_threshold}
          confidence={finding.confidence}
          status={finding.evidence_json?.status}
        />
        <span className="text-xs text-slate-400 font-mono">
          Severity: <span className="text-slate-200 font-medium">{finding.severity}</span>
        </span>
      </div>

      {/* Assistive Explanation */}
      <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
        {finding.explanation}
      </p>

      {/* Clinician comment if reviewed */}
      {finding.clinician_comment && (
        <div className="mt-2 text-xs bg-indigo-950/30 border border-indigo-500/30 rounded-lg p-2.5 text-indigo-200">
          <span className="font-semibold text-indigo-300 block mb-0.5">Clinician Note ({finding.reviewed_at ? new Date(finding.reviewed_at).toLocaleDateString() : "Reviewed"}):</span>
          {finding.clinician_comment}
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-4 pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onViewLocalization(finding)}
            className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            View Localization
          </button>

          <button
            onClick={() => onViewEvidence(finding)}
            className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Evidence Provenance
          </button>
        </div>

        {/* Review Action */}
        <button
          onClick={() => onOpenReview(finding)}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition"
        >
          {finding.review_status === "PENDING" ? "Perform Review" : "Edit Review"}
        </button>
      </div>
    </div>
  );
};
