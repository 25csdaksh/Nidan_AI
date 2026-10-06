"use client";

import React, { useState } from "react";
import { ImagingFinding, ImagingFindingReviewStatus } from "@/lib/types";

interface ImagingReviewModalProps {
  finding: ImagingFinding;
  isOpen: boolean;
  onClose: () => void;
  onSubmitReview: (findingId: string, status: ImagingFindingReviewStatus, comment: string, modifiedSeverity?: string) => Promise<void>;
}

export const ImagingReviewModal: React.FC<ImagingReviewModalProps> = ({
  finding,
  isOpen,
  onClose,
  onSubmitReview,
}) => {
  const [selectedStatus, setSelectedStatus] = useState<ImagingFindingReviewStatus>(
    finding.review_status === "PENDING" ? "ACCEPTED" : finding.review_status
  );
  const [comment, setComment] = useState(finding.clinician_comment || "");
  const [severity, setSeverity] = useState(finding.severity);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmitReview(
        finding.id,
        selectedStatus,
        comment,
        selectedStatus === "MODIFIED" ? severity : undefined
      );
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to submit clinician review.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-lg shadow-2xl p-6 text-slate-100 relative">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-lg font-bold text-slate-100">Clinician Finding Review</h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              {finding.finding_name} ({finding.finding_code})
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Model Output Snapshot */}
        <div className="my-4 p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs space-y-1.5">
          <div className="flex justify-between text-slate-300">
            <span>Model Calibrated Probability:</span>
            <span className="font-mono font-bold text-indigo-300">{Math.round(finding.probability * 100)}%</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Decision Threshold:</span>
            <span className="font-mono">{Math.round(finding.model_threshold * 100)}%</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Original Model Confidence:</span>
            <span className="font-mono">{Math.round(finding.confidence * 100)}%</span>
          </div>
          <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-800/60 italic">
            *Original model output is immutable and preserved for clinical audit.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Action Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Review Decision
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setSelectedStatus("ACCEPTED")}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold transition ${
                  selectedStatus === "ACCEPTED"
                    ? "bg-emerald-600 text-white border-emerald-500 shadow-md shadow-emerald-950/50"
                    : "bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-700"
                }`}
              >
                ACCEPT
              </button>
              <button
                type="button"
                onClick={() => setSelectedStatus("MODIFIED")}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold transition ${
                  selectedStatus === "MODIFIED"
                    ? "bg-sky-600 text-white border-sky-500 shadow-md shadow-sky-950/50"
                    : "bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-700"
                }`}
              >
                MODIFY
              </button>
              <button
                type="button"
                onClick={() => setSelectedStatus("REJECTED")}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold transition ${
                  selectedStatus === "REJECTED"
                    ? "bg-rose-600 text-white border-rose-500 shadow-md shadow-rose-950/50"
                    : "bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-700"
                }`}
              >
                REJECT
              </button>
            </div>
          </div>

          {/* If Modified, allow severity adjustment */}
          {selectedStatus === "MODIFIED" && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Adjusted Clinical Severity
              </label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200"
              >
                <option value="INFO">INFO / Incidental</option>
                <option value="LOW">LOW</option>
                <option value="MODERATE">MODERATE</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>
          )}

          {/* Clinical Comments */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Clinician Clinical Interpretation / Notes <span className="text-slate-500">(Mandatory for Reject/Modify)</span>
            </label>
            <textarea
              rows={3}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Document clinical rationale, radiographic correlation, or artifacts..."
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {error && (
            <div className="p-2.5 rounded-lg bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
              {error}
            </div>
          )}

          {/* Footer Actions */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition disabled:opacity-50"
            >
              {isSubmitting ? "Recording Review..." : "Confirm & Save Review"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
