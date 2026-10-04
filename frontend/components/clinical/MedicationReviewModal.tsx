"use client";

import React, { useState } from "react";
import { MedicationSafetyFinding, MedicationReviewStatus } from "@/lib/types";
import {
  CheckCircle2,
  XCircle,
  Edit3,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";

interface MedicationReviewModalProps {
  finding: MedicationSafetyFinding | null;
  onClose: () => void;
  onSubmitReview: (findingId: string, status: MedicationReviewStatus, note: string) => Promise<void>;
}

export const MedicationReviewModal: React.FC<MedicationReviewModalProps> = ({
  finding,
  onClose,
  onSubmitReview,
}) => {
  const [reviewStatus, setReviewStatus] = useState<MedicationReviewStatus>("ACCEPTED");
  const [clinicianNote, setClinicianNote] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!finding) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clinicianNote.trim()) {
      setError("Please provide a clinician justification note for HIPAA audit compliance.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onSubmitReview(finding.id, reviewStatus, clinicianNote.trim());
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to submit review");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in duration-150">
        <div className="flex justify-between items-center pb-3 border-b border-slate-800">
          <h4 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
            Clinician Medication Alert Review
          </h4>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-sm font-bold"
          >
            ✕
          </button>
        </div>

        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
          <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider block">
            {finding.finding_type.replace(/_/g, " ")} • {finding.severity}
          </span>
          <h5 className="text-sm font-bold text-slate-100">{finding.title}</h5>
          <p className="text-xs text-slate-400">{finding.description}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 block">
              Review Determination:
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setReviewStatus("ACCEPTED")}
                className={`py-2 px-3 rounded-lg text-xs font-bold border transition flex items-center justify-center gap-1.5 ${
                  reviewStatus === "ACCEPTED"
                    ? "bg-emerald-950 text-emerald-300 border-emerald-500 shadow-sm"
                    : "bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800"
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Accept
              </button>
              <button
                type="button"
                onClick={() => setReviewStatus("MODIFIED")}
                className={`py-2 px-3 rounded-lg text-xs font-bold border transition flex items-center justify-center gap-1.5 ${
                  reviewStatus === "MODIFIED"
                    ? "bg-blue-950 text-blue-300 border-blue-500 shadow-sm"
                    : "bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800"
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" /> Modify
              </button>
              <button
                type="button"
                onClick={() => setReviewStatus("REJECTED")}
                className={`py-2 px-3 rounded-lg text-xs font-bold border transition flex items-center justify-center gap-1.5 ${
                  reviewStatus === "REJECTED"
                    ? "bg-rose-950 text-rose-300 border-rose-500 shadow-sm"
                    : "bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800"
                }`}
              >
                <XCircle className="w-3.5 h-3.5" /> Dismiss
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 block">
              Clinician Justification & Audit Note:
            </label>
            <textarea
              rows={3}
              value={clinicianNote}
              onChange={(e) => setClinicianNote(e.target.value)}
              placeholder="e.g. Discussed interaction with patient; ordered coagulation monitoring."
              className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs p-3 rounded-lg focus:outline-none focus:border-cyan-500 placeholder-slate-600"
            />
          </div>

          {error && (
            <div className="p-2.5 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-lg flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="pt-3 border-t border-slate-800 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow transition disabled:opacity-50"
            >
              {isSubmitting ? "Submitting Review..." : "Confirm Review"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
