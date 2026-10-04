"use client";

import React, { useState } from "react";
import { CopilotMessage as CopilotMessageType, EvidenceItem } from "@/lib/types";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  ThumbsUp,
  ThumbsDown,
  Info,
  ExternalLink,
  Bot,
  User as UserIcon,
} from "lucide-react";
import { submitCopilotFeedback } from "@/lib/api";

interface CopilotMessageProps {
  message: CopilotMessageType;
  onSelectEvidence: (evidenceId: string) => void;
  evidenceItemsMap: Map<string, EvidenceItem>;
}

export function CopilotMessage({
  message,
  onSelectEvidence,
  evidenceItemsMap,
}: CopilotMessageProps) {
  const isUser = message.role === "user";
  const [feedbackSent, setFeedbackSent] = useState<"HELPFUL" | "NOT_HELPFUL" | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const struct = message.structured_response;

  const handleFeedback = async (rating: "HELPFUL" | "NOT_HELPFUL") => {
    if (feedbackSent || submitting) return;
    setSubmitting(true);
    try {
      await submitCopilotFeedback(message.id, {
        rating,
        feedback_category: rating === "HELPFUL" ? "HELPFUL" : "NOT_HELPFUL",
      });
      setFeedbackSent(rating);
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  // Helper to render text with clickable [EVID-...] tags
  const renderFormattedText = (text: string) => {
    const parts = text.split(/(\[EVID-[A-Z0-9-]+\]|EVID-[A-Z0-9-]+)/g);
    return parts.map((part, index) => {
      const cleanTag = part.replace(/[\[\]]/g, "");
      if (cleanTag.startsWith("EVID-")) {
        const item = evidenceItemsMap.get(cleanTag);
        return (
          <button
            key={index}
            onClick={() => onSelectEvidence(cleanTag)}
            className="inline-flex items-center gap-1 font-mono text-[11px] font-bold px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 hover:bg-sky-500/30 hover:text-sky-200 transition-colors mx-0.5"
            title={`View evidence: ${item?.title || cleanTag}`}
          >
            <span>{cleanTag}</span>
            <ExternalLink className="w-2.5 h-2.5" />
          </button>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className={`flex gap-3 text-sm ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shrink-0 shadow-md">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}

      <div
        className={`max-w-[85%] rounded-2xl p-4 space-y-3 ${
          isUser
            ? "bg-sky-600 text-white shadow-lg rounded-tr-sm"
            : "bg-slate-900 border border-slate-800 text-slate-200 shadow-xl rounded-tl-sm"
        }`}
      >
        {/* Header Badges for Assistant Message */}
        {!isUser && struct && (
          <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              {struct.safety_status === "PASSED" ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  <ShieldCheck className="w-3 h-3" /> Safety Verified
                </span>
              ) : struct.safety_status === "PROHIBITED_REQUEST" ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  <ShieldAlert className="w-3 h-3" /> CDSS Safety Boundary
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                  <AlertTriangle className="w-3 h-3" /> {struct.safety_status}
                </span>
              )}
              <span className="text-[11px] font-mono text-slate-400">
                {struct.query_type}
              </span>
            </div>

            {struct.requires_clinician_review && (
              <span className="text-[10px] font-medium text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                Clinician Review Required
              </span>
            )}
          </div>
        )}

        {/* Message Main Body */}
        <div className="whitespace-pre-wrap leading-relaxed text-[13px]">
          {renderFormattedText(message.content)}
        </div>

        {/* Structured Evidence Claims */}
        {!isUser && struct && struct.claims && struct.claims.length > 0 && (
          <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              Verified Evidence Claims ({struct.claims.length}):
            </div>
            <div className="space-y-1">
              {struct.claims.map((claim, idx) => (
                <div
                  key={idx}
                  className="text-xs p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-start justify-between gap-2"
                >
                  <div className="flex-1 text-slate-300">
                    <span className="text-slate-400 font-medium">#{idx + 1}: </span>
                    {claim.claim}
                  </div>
                  <div className="flex flex-wrap gap-1 shrink-0">
                    {claim.evidence_ids.map((eid) => (
                      <button
                        key={eid}
                        onClick={() => onSelectEvidence(eid)}
                        className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 hover:bg-sky-500/20"
                      >
                        {eid}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Limitations & Data Quality Notes */}
        {!isUser && struct && struct.limitations && struct.limitations.length > 0 && (
          <div className="pt-2 border-t border-slate-800/60 text-[11px] text-amber-300/80 space-y-1">
            <div className="font-semibold flex items-center gap-1 text-amber-400">
              <Info className="w-3 h-3" /> Data Considerations & Limitations:
            </div>
            <ul className="list-disc list-inside space-y-0.5 pl-1">
              {struct.limitations.map((lim, idx) => (
                <li key={idx}>{lim}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Assistant Footer with Feedback Actions */}
        {!isUser && (
          <div className="pt-2 flex items-center justify-between text-[11px] text-slate-500">
            <div className="flex items-center gap-2">
              <span>{struct?.records_included ?? 0} evidence records cited</span>
              <span>•</span>
              <span className="font-mono">v{struct?.context_version || "1.0"}</span>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-slate-400">Helpful?</span>
              <button
                type="button"
                disabled={feedbackSent !== null || submitting}
                onClick={() => handleFeedback("HELPFUL")}
                className={`p-1 rounded hover:bg-slate-800 transition-colors ${
                  feedbackSent === "HELPFUL" ? "text-emerald-400 bg-emerald-500/10" : "text-slate-400 hover:text-slate-200"
                }`}
                title="Helpful clinical answer"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                disabled={feedbackSent !== null || submitting}
                onClick={() => handleFeedback("NOT_HELPFUL")}
                className={`p-1 rounded hover:bg-slate-800 transition-colors ${
                  feedbackSent === "NOT_HELPFUL" ? "text-rose-400 bg-rose-500/10" : "text-slate-400 hover:text-slate-200"
                }`}
                title="Not helpful or incomplete"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 shadow-md">
          <UserIcon className="w-4 h-4 text-slate-300" />
        </div>
      )}
    </div>
  );
}
