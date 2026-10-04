"use client";

import React from "react";
import { EvidenceItem } from "@/lib/types";
import { X, FileText, CheckCircle2, AlertTriangle, Activity, Pill, ShieldCheck } from "lucide-react";

interface CopilotEvidenceDrawerProps {
  evidence: EvidenceItem | null;
  onClose: () => void;
}

export function CopilotEvidenceDrawer({ evidence, onClose }: CopilotEvidenceDrawerProps) {
  if (!evidence) return null;

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "LAB_RESULT":
      case "CLINICAL_FINDING":
      case "LONGITUDINAL_TREND":
        return <Activity className="w-5 h-5 text-sky-400" />;
      case "MEDICATION":
      case "PRESCRIPTION":
        return <Pill className="w-5 h-5 text-emerald-400" />;
      case "MEDICATION_SAFETY":
        return <AlertTriangle className="w-5 h-5 text-amber-400" />;
      default:
        return <FileText className="w-5 h-5 text-purple-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl p-6 overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            {getTypeIcon(evidence.type)}
            <div>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
                {evidence.evidence_id}
              </span>
              <h3 className="text-sm font-bold text-slate-100 mt-1">
                {evidence.title || "Clinical Evidence Details"}
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-4 py-4 text-sm text-slate-300">
          {/* Main Value & Status */}
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
            <div className="text-xs font-medium text-slate-400">Observed Value / Entity</div>
            <div className="text-lg font-bold text-slate-100 mt-1">
              {evidence.value || "Present in Record"} {evidence.unit || ""}
            </div>
            {evidence.reference_range && (
              <div className="text-xs text-slate-400 mt-1">
                Reference Range: <span className="text-slate-200">{evidence.reference_range}</span>
              </div>
            )}
            {evidence.status && (
              <div className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-900 border border-slate-700 text-amber-300">
                Status: {evidence.status}
              </div>
            )}
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-400">Observation Date</span>
              <div className="font-semibold text-slate-200 mt-0.5">{evidence.date || "Unknown"}</div>
            </div>
            <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-400">Review Status</span>
              <div className="font-semibold text-emerald-300 mt-0.5">{evidence.review_status || "EXTRACTED"}</div>
            </div>
            {evidence.confidence !== undefined && (
              <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-400">Extraction Confidence</span>
                <div className="font-semibold text-sky-300 mt-0.5">{(evidence.confidence * 100).toFixed(0)}%</div>
              </div>
            )}
            {evidence.rule_id && (
              <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-400">Rule Identifier</span>
                <div className="font-mono font-semibold text-purple-300 mt-0.5">{evidence.rule_id}</div>
              </div>
            )}
          </div>

          {/* Source Text Provenance */}
          {evidence.source_text && (
            <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3">
              <span className="text-xs font-semibold text-slate-400">Raw Source Document Snippet:</span>
              <p className="text-xs font-mono text-slate-300 mt-1.5 p-2 bg-slate-900 rounded border border-slate-800/80 break-words">
                "{evidence.source_text}"
              </p>
            </div>
          )}

          {/* Additional Structured Details */}
          {evidence.details && Object.keys(evidence.details).length > 0 && (
            <div className="bg-slate-800/30 border border-slate-800 rounded-lg p-3 space-y-1.5">
              <span className="text-xs font-semibold text-slate-400">Clinical Attributes:</span>
              {Object.entries(evidence.details).map(([k, v]) => (
                <div key={k} className="text-xs flex justify-between py-1 border-b border-slate-800/50 last:border-0">
                  <span className="text-slate-400 capitalize">{k.replace(/_/g, " ")}:</span>
                  <span className="text-slate-200 font-medium text-right max-w-[200px] truncate">{String(v)}</span>
                </div>
              ))}
            </div>
          )}

          {/* Mandatory Provenance Notice */}
          <div className="pt-4 border-t border-slate-800 text-[11px] text-slate-500 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0" />
            <span>Traceable evidence provenance verified by NIDAN AI ingestion engine.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
