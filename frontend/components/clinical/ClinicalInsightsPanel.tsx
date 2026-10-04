"use client";

import React, { useState } from "react";
import {
  ClinicalAnalysis,
  ClinicalFinding,
  FindingStatus,
  FindingType,
} from "@/lib/types";
import {
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Info,
  ShieldAlert,
  Activity,
  ChevronDown,
  ChevronUp,
  FileText,
  UserCheck,
  Check,
  X,
  Edit3,
  Search,
  Sparkles,
  Layers,
} from "lucide-react";
import { reviewClinicalFinding, triggerClinicalAnalysis } from "@/lib/api";

interface ClinicalInsightsPanelProps {
  documentId: string;
  analysis: ClinicalAnalysis | null;
  onAnalysisUpdate?: (updated: ClinicalAnalysis) => void;
  onClose?: () => void;
}

export function ClinicalInsightsPanel({
  documentId,
  analysis,
  onAnalysisUpdate,
  onClose,
}: ClinicalInsightsPanelProps) {
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [reviewingFinding, setReviewingFinding] = useState<ClinicalFinding | null>(null);
  const [modifyTitle, setModifyTitle] = useState("");
  const [modifyExplanation, setModifyExplanation] = useState("");
  const [reviewerNotes, setReviewerNotes] = useState("");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});

  const handleReanalyze = async () => {
    try {
      setIsReanalyzing(true);
      const res = await triggerClinicalAnalysis(documentId, true);
      if (onAnalysisUpdate) {
        onAnalysisUpdate(res);
      }
    } catch (err: any) {
      alert(err.message || "Re-analysis failed");
    } finally {
      setIsReanalyzing(false);
    }
  };

  const handleQuickReview = async (finding: ClinicalFinding, action: "ACCEPTED" | "REJECTED") => {
    try {
      const res = await reviewClinicalFinding(finding.id, {
        review_status: action,
        reviewer_notes: `Clinician quick-action: ${action}`,
      });
      if (analysis && onAnalysisUpdate) {
        const updatedFindings = analysis.findings.map((f) => (f.id === finding.id ? res : f));
        onAnalysisUpdate({ ...analysis, findings: updatedFindings });
      }
    } catch (err: any) {
      alert(err.message || "Failed to submit review");
    }
  };

  const handleDetailedReviewSubmit = async (status: "ACCEPTED" | "MODIFIED" | "REJECTED") => {
    if (!reviewingFinding) return;
    try {
      setIsSubmittingReview(true);
      const res = await reviewClinicalFinding(reviewingFinding.id, {
        review_status: status,
        modified_title: modifyTitle || undefined,
        modified_explanation: modifyExplanation || undefined,
        reviewer_notes: reviewerNotes || undefined,
      });
      if (analysis && onAnalysisUpdate) {
        const updatedFindings = analysis.findings.map((f) => (f.id === reviewingFinding.id ? res : f));
        onAnalysisUpdate({ ...analysis, findings: updatedFindings });
      }
      setReviewingFinding(null);
    } catch (err: any) {
      alert(err.message || "Failed to submit review");
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const findings = analysis?.findings || [];

  const filteredFindings = findings.filter((f) => {
    if (selectedFilter === "CRITICAL" && f.severity !== "CRITICAL") return false;
    if (selectedFilter === "ABNORMAL" && f.status !== "LOW" && f.status !== "HIGH") return false;
    if (selectedFilter === "PATTERN" && f.finding_type !== "PATTERN") return false;
    if (selectedFilter === "DEFICIENCY" && f.finding_type !== "POSSIBLE_DEFICIENCY") return false;
    if (selectedFilter === "WARNINGS" && f.finding_type !== "DATA_QUALITY_WARNING") return false;

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        f.title.toLowerCase().includes(q) ||
        (f.analyte && f.analyte.toLowerCase().includes(q)) ||
        f.explanation.toLowerCase().includes(q) ||
        (f.clinical_association && f.clinical_association.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const getStatusBadge = (status: FindingStatus) => {
    switch (status) {
      case "CRITICAL_LOW":
      case "CRITICAL_HIGH":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse">
            <AlertOctagon className="w-3.5 h-3.5" />
            CRITICAL
          </span>
        );
      case "LOW":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5" />
            LOW
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-500/20 text-orange-400 border border-orange-500/30">
            <AlertTriangle className="w-3.5 h-3.5" />
            HIGH
          </span>
        );
      case "NORMAL":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" />
            WITHIN RANGE
          </span>
        );
      case "REFERENCE_RANGE_UNRESOLVED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            <Info className="w-3.5 h-3.5" />
            DEMOGRAPHIC UNRESOLVED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-400 border border-slate-500/30">
            <Info className="w-3.5 h-3.5" />
            REVIEW REQUIRED
          </span>
        );
    }
  };

  const getFindingTypeBadge = (type: FindingType) => {
    switch (type) {
      case "PATTERN":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-purple-500/15 text-purple-300 border border-purple-500/20">
            <Layers className="w-3 h-3" />
            Multi-Marker Pattern
          </span>
        );
      case "POSSIBLE_DEFICIENCY":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/20">
            <Activity className="w-3 h-3" />
            Potential Deficiency
          </span>
        );
      case "CRITICAL_LAB":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-rose-500/15 text-rose-300 border border-rose-500/20">
            <AlertOctagon className="w-3 h-3" />
            Critical Threshold Alert
          </span>
        );
      case "DATA_QUALITY_WARNING":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/15 text-blue-300 border border-blue-500/20">
            <Info className="w-3 h-3" />
            Data Quality Warning
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-500/15 text-slate-300 border border-slate-500/20">
            <Activity className="w-3 h-3" />
            Laboratory Analyte
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 rounded-xl border border-slate-800 shadow-2xl overflow-hidden">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border-b border-slate-800 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-indigo-500/20 border border-indigo-500/30 text-indigo-400">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-wide">
                Clinical Anomaly & Blood Report Intelligence Engine
              </h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                Phase 3 Engine v{analysis?.rule_set_version || "1.0.0"}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Deterministic, unit-aware reference range resolution & multi-marker pattern inference
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleReanalyze}
            disabled={isReanalyzing}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-md shadow-indigo-600/20 disabled:opacity-50"
          >
            <Activity className={`w-3.5 h-3.5 ${isReanalyzing ? "animate-spin" : ""}`} />
            {isReanalyzing ? "Evaluating Rules..." : "Re-evaluate Findings"}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* Mandatory CDSS Level 1 & 2 Disclaimer */}
      <div className="bg-amber-950/40 border-b border-amber-800/40 px-6 py-2.5 flex items-center gap-2.5 text-xs text-amber-300">
        <ShieldAlert className="w-4 h-4 flex-shrink-0 text-amber-400" />
        <span>
          <strong>CDSS Advisory Notice:</strong> NIDAN AI provides clinical decision support to assist licensed clinicians. It does not provide autonomous medical diagnosis, prescriptions, or treatment decisions. Clinical correlation is required.
        </span>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-6 bg-slate-900/40 border-b border-slate-800">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 flex flex-col">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Findings</span>
          <span className="text-2xl font-bold text-white mt-1">{analysis?.findings_count || 0}</span>
        </div>

        <div className="bg-rose-950/20 border border-rose-900/30 rounded-lg p-3.5 flex flex-col">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-rose-400 uppercase tracking-wider">Critical Alerts</span>
            <AlertOctagon className="w-4 h-4 text-rose-400" />
          </div>
          <span className="text-2xl font-bold text-rose-300 mt-1">{analysis?.critical_count || 0}</span>
        </div>

        <div className="bg-amber-950/20 border border-amber-900/30 rounded-lg p-3.5 flex flex-col">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-amber-400 uppercase tracking-wider">Abnormalities</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <span className="text-2xl font-bold text-amber-300 mt-1">{analysis?.abnormal_count || 0}</span>
        </div>

        <div className="bg-purple-950/20 border border-purple-900/30 rounded-lg p-3.5 flex flex-col">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-purple-400 uppercase tracking-wider">Pattern Findings</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <span className="text-2xl font-bold text-purple-300 mt-1">{analysis?.pattern_count || 0}</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 flex flex-col">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Knowledge Base</span>
            <FileText className="w-4 h-4 text-indigo-400" />
          </div>
          <span className="text-xs font-semibold text-indigo-300 mt-2 truncate">
            Catalog v{analysis?.reference_range_version || "2026.1"}
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="px-6 py-3 border-b border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/20">
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {[
            { id: "ALL", label: "All Findings" },
            { id: "CRITICAL", label: "🔴 Critical" },
            { id: "ABNORMAL", label: "🟠 Abnormal" },
            { id: "PATTERN", label: "🟣 Patterns" },
            { id: "DEFICIENCY", label: "🟡 Deficiencies" },
            { id: "WARNINGS", label: "ℹ️ Quality Warnings" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                selectedFilter === tab.id
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20 font-semibold"
                  : "bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search analyte or finding..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
      </div>

      {/* Findings List Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {filteredFindings.length === 0 ? (
          <div className="text-center py-16">
            <CheckCircle2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-300">No findings match your filter</h3>
            <p className="text-xs text-slate-500 mt-1">All evaluated laboratory entities are within specified ranges or cleared.</p>
          </div>
        ) : (
          filteredFindings.map((finding) => (
            <div
              key={finding.id}
              className={`rounded-xl border transition-all ${
                finding.severity === "CRITICAL"
                  ? "bg-rose-950/10 border-rose-800/40 hover:border-rose-700/60"
                  : finding.finding_type === "PATTERN"
                  ? "bg-purple-950/10 border-purple-800/40 hover:border-purple-700/60"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              } p-5`}
            >
              {/* Card Top Row */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/60">
                <div className="flex items-center gap-2.5 flex-wrap">
                  {getStatusBadge(finding.status)}
                  {getFindingTypeBadge(finding.finding_type)}
                  <h3 className="text-sm font-bold text-white tracking-tight">{finding.title}</h3>
                </div>

                <div className="flex items-center gap-2">
                  {finding.review_status === "PENDING" ? (
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
                      Pending Doctor Review
                    </span>
                  ) : (
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold flex items-center gap-1 ${
                        finding.review_status === "ACCEPTED"
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          : finding.review_status === "MODIFIED"
                          ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                          : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                      }`}
                    >
                      <UserCheck className="w-3 h-3" />
                      Doctor {finding.review_status}
                    </span>
                  )}

                  <div className="text-[11px] text-slate-400 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700">
                    Rule: <span className="text-slate-200 font-mono">{finding.rule_id}</span>
                  </div>
                </div>
              </div>

              {/* Card Middle: Values & Ranges */}
              {finding.analyte && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-3.5 bg-slate-950/40 p-3 rounded-lg border border-slate-800/80">
                  <div>
                    <span className="text-[11px] text-slate-400">Analyte Marker</span>
                    <p className="text-sm font-semibold text-slate-200">{finding.analyte}</p>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-400">Reported Observed Value</span>
                    <p className="text-sm font-bold text-white">
                      {finding.value || "N/A"} <span className="text-xs font-normal text-slate-400">{finding.unit}</span>
                    </p>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-400">Reference Source & Version</span>
                    <p className="text-xs text-indigo-300 font-medium truncate">
                      {finding.reference_source} {finding.reference_source_version && `(${finding.reference_source_version})`}
                    </p>
                  </div>
                </div>
              )}

              {/* Card Explanations & Clinical Associations */}
              <div className="space-y-2 mt-2">
                <p className="text-xs text-slate-300 leading-relaxed">
                  <strong className="text-slate-200">Observation:</strong> {finding.explanation}
                </p>

                {finding.clinical_association && (
                  <div className="p-2.5 rounded bg-indigo-950/30 border border-indigo-900/40 text-xs text-indigo-200">
                    <strong className="text-indigo-300">Controlled Association:</strong> {finding.clinical_association}
                  </div>
                )}

                {finding.reviewer_notes && (
                  <div className="p-2.5 rounded bg-emerald-950/20 border border-emerald-900/30 text-xs text-emerald-300">
                    <strong className="text-emerald-400">Doctor Note:</strong> {finding.reviewer_notes}
                  </div>
                )}
              </div>

              {/* Traceable Evidence Accordion */}
              {finding.evidence && finding.evidence.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-800/60">
                  <button
                    onClick={() =>
                      setExpandedEvidence((prev) => ({
                        ...prev,
                        [finding.id]: !prev[finding.id],
                      }))
                    }
                    className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors font-medium"
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>
                      {expandedEvidence[finding.id] ? "Hide" : "View"} Traceable Supporting Evidence ({finding.evidence.length} marker{finding.evidence.length > 1 ? "s" : ""})
                    </span>
                    {expandedEvidence[finding.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {expandedEvidence[finding.id] && (
                    <div className="mt-2.5 space-y-2 bg-slate-950 p-3 rounded-lg border border-slate-800">
                      {finding.evidence.map((ev, idx) => (
                        <div
                          key={idx}
                          className="flex flex-col sm:flex-row sm:items-center justify-between text-xs p-2 rounded bg-slate-900/80 border border-slate-800/80 gap-2"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-slate-200">{ev.analyte}:</span>
                            <span className="text-white font-mono bg-slate-800 px-1.5 py-0.5 rounded">
                              {ev.value} {ev.unit}
                            </span>
                            {ev.status && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                {ev.status}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-slate-400 text-[11px]">
                            {ev.page_number && <span>Page {ev.page_number}</span>}
                            <span>Confidence: {Math.round((ev.confidence || 1) * 100)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Clinician Review Quick Action Bar */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
                <div className="text-[11px] text-slate-500">
                  Confidence Score: <span className="font-semibold text-slate-300">{Math.round(finding.confidence * 100)}%</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleQuickReview(finding, "ACCEPTED")}
                    className="px-2.5 py-1 rounded text-xs font-medium bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 transition-colors flex items-center gap-1"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Accept
                  </button>

                  <button
                    onClick={() => {
                      setReviewingFinding(finding);
                      setModifyTitle(finding.title);
                      setModifyExplanation(finding.explanation);
                      setReviewerNotes(finding.reviewer_notes || "");
                    }}
                    className="px-2.5 py-1 rounded text-xs font-medium bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-colors flex items-center gap-1"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Modify
                  </button>

                  <button
                    onClick={() => handleQuickReview(finding, "REJECTED")}
                    className="px-2.5 py-1 rounded text-xs font-medium bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 transition-colors flex items-center gap-1"
                  >
                    <X className="w-3.5 h-3.5" />
                    Reject
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Review Modal */}
      {reviewingFinding && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-indigo-400" />
                Doctor Adjudication & Finding Modification
              </h3>
              <button
                onClick={() => setReviewingFinding(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">
                  Finding Title
                </label>
                <input
                  type="text"
                  value={modifyTitle}
                  onChange={(e) => setModifyTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">
                  Finding Explanation
                </label>
                <textarea
                  rows={3}
                  value={modifyExplanation}
                  onChange={(e) => setModifyExplanation(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">
                  Clinician Adjudication Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="Record rationale for audit trail..."
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                onClick={() => setReviewingFinding(null)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={isSubmittingReview}
                onClick={() => handleDetailedReviewSubmit("MODIFIED")}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50"
              >
                {isSubmittingReview ? "Saving..." : "Save Modifications"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
