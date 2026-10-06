"use client";

import React from "react";
import { ImagingAnalysis, ImagingFinding } from "@/lib/types";
import { ImagingFindingCard } from "./ImagingFindingCard";

interface ImagingAnalysisPanelProps {
  analysis: ImagingAnalysis;
  onViewLocalization: (finding: ImagingFinding) => void;
  onViewEvidence: (finding: ImagingFinding) => void;
  onOpenReview: (finding: ImagingFinding) => void;
}

export const ImagingAnalysisPanel: React.FC<ImagingAnalysisPanelProps> = ({
  analysis,
  onViewLocalization,
  onViewEvidence,
  onOpenReview,
}) => {
  const findings = analysis.findings || [];
  const aboveThresholdCount = findings.filter((f) => f.probability >= f.model_threshold).length;
  const acceptedCount = findings.filter((f) => f.review_status === "ACCEPTED").length;

  const isTorchVision = analysis.model_id.includes("PYTORCH") || analysis.model_id.includes("TORCHXRAYVISION");
  const isHeuristic = analysis.model_id.includes("NATIVE_VISION");
  const isTestHarness = analysis.model_id.includes("FOUNDATION") || analysis.output_json?.is_demo_mock;

  return (
    <div className="space-y-4">
      {/* Model Classification & Safety Banners */}
      {isTorchVision && (
        <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-200 text-xs flex items-start gap-2.5">
          <span className="font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/50 text-[10px] whitespace-nowrap mt-0.5">
            Pretrained DenseNet-121
          </span>
          <div>
            <span className="font-semibold text-emerald-100">TorchXRayVision DenseNet-121 Weights Activated:</span>
            <span className="text-emerald-300 ml-1">
              Multi-label deep learning feature extraction executed with verified SHA-256 integrity. Outputs represent uncalibrated multi-label sigmoid scores. 
              <strong> Clinical validation not performed.</strong> Mandatory radiologist/physician review required for all findings.
            </span>
          </div>
        </div>
      )}

      {isHeuristic && (
        <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs flex items-center gap-2">
          <span className="font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/50 text-[10px] whitespace-nowrap">
            Experimental Heuristic
          </span>
          <span>
            Output derived from handcrafted spatial image heuristics. Not a validated statistical or deep learning model. Mandatory clinician verification required.
          </span>
        </div>
      )}

      {isTestHarness && !isTorchVision && (
        <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-700/60 text-slate-300 text-xs flex items-center gap-2">
          <span className="font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/50 text-indigo-300 text-[10px] whitespace-nowrap">
            Demo / Test Harness
          </span>
          <span>
            Model output generated from deterministic test harness for software verification. Not for clinical diagnostic use.
          </span>
        </div>
      )}

      {/* Analysis Metadata Header */}
      <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 text-xs text-slate-300 flex flex-wrap items-center justify-between gap-3 shadow-lg">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <span className="text-slate-500 block">Model Run:</span>
            <span className="font-semibold text-slate-100 font-mono">{analysis.model_id} (v{analysis.model_version})</span>
          </div>
          <div className="h-6 w-px bg-slate-800 hidden sm:block" />
          <div>
            <span className="text-slate-500 block">Preprocessing:</span>
            <span className="font-mono text-slate-300">{analysis.preprocessing_version}</span>
          </div>
          <div className="h-6 w-px bg-slate-800 hidden sm:block" />
          <div>
            <span className="text-slate-500 block">Latency:</span>
            <span className="font-mono text-indigo-300">{analysis.processing_time_ms || 0} ms</span>
          </div>
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono">
            {findings.length} findings evaluated
          </span>
          <span className="px-2.5 py-1 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-500/40 font-mono font-medium">
            {aboveThresholdCount} above threshold
          </span>
          <span className="px-2.5 py-1 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40 font-mono font-medium">
            {acceptedCount} clinician verified
          </span>
        </div>
      </div>

      {/* Findings List */}
      <div className="space-y-3">
        {findings.map((finding) => (
          <ImagingFindingCard
            key={finding.id}
            finding={finding}
            onViewLocalization={onViewLocalization}
            onViewEvidence={onViewEvidence}
            onOpenReview={onOpenReview}
          />
        ))}
      </div>
    </div>
  );
};
