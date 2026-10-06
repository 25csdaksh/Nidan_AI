"use client";

import React from "react";
import { ImagingFinding } from "@/lib/types";

interface ImagingEvidenceDrawerProps {
  finding: ImagingFinding | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ImagingEvidenceDrawer: React.FC<ImagingEvidenceDrawerProps> = ({
  finding,
  isOpen,
  onClose,
}) => {
  if (!isOpen || !finding) return null;

  const evId = `EVID-XRAY-${finding.id.slice(0, 8).toUpperCase()}`;
  const evDetails = finding.evidence_json || {};

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-slate-900 border-l border-slate-700/80 h-full p-6 overflow-y-auto text-slate-100 flex flex-col justify-between shadow-2xl">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
                Verifiable Evidence Provenance
              </span>
              <h3 className="text-base font-bold text-slate-100 mt-2 font-mono text-indigo-300">
                {evId}
              </h3>
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

          {/* Finding Details */}
          <div className="mt-4 space-y-4 text-xs">
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <h4 className="font-semibold text-slate-200 mb-2">Radiographic Finding</h4>
              <div className="space-y-1 font-mono text-slate-300">
                <div className="flex justify-between">
                  <span className="text-slate-500">Finding:</span>
                  <span>{finding.finding_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Code:</span>
                  <span>{finding.finding_code}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Region:</span>
                  <span>{finding.anatomical_region}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Review Status:</span>
                  <span className="font-semibold text-indigo-300">{finding.review_status}</span>
                </div>
              </div>
            </div>

            {/* Neural Probabilities & Calibration */}
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <h4 className="font-semibold text-slate-200 mb-2">Model Calibration & Metrics</h4>
              <div className="space-y-1 font-mono text-slate-300">
                <div className="flex justify-between">
                  <span className="text-slate-500">Calibrated Probability:</span>
                  <span className="font-bold text-amber-400">{Math.round(finding.probability * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Raw Model Logit Prob:</span>
                  <span>{evDetails.raw_probability ? Math.round(evDetails.raw_probability * 100) : "N/A"}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Decision Threshold:</span>
                  <span>{Math.round(finding.model_threshold * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Confidence Score:</span>
                  <span>{Math.round(finding.confidence * 100)}%</span>
                </div>
              </div>
            </div>

            {/* Pipeline Provenance */}
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <h4 className="font-semibold text-slate-200 mb-2">Pipeline Reproducibility Hashes</h4>
              <div className="space-y-1.5 font-mono text-[11px] text-slate-400 break-all">
                <div>
                  <span className="text-slate-500 block">Finding UUID:</span>
                  <span className="text-slate-300">{finding.id}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Analysis UUID:</span>
                  <span className="text-slate-300">{finding.imaging_analysis_id}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Preprocessing Version:</span>
                  <span className="text-slate-300">xray-preprocess-v1</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Model Version:</span>
                  <span className="text-slate-300">{evDetails.model_version || "1.0.0"}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-slate-800 mt-6">
          <button
            onClick={onClose}
            className="w-full py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            Close Provenance
          </button>
        </div>
      </div>
    </div>
  );
};
