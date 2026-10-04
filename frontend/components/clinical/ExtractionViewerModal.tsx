"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  Download,
  Edit2,
  ExternalLink,
  Eye,
  FileCheck,
  FileText,
  Filter,
  RefreshCw,
  Shield,
  Sparkles,
  X,
  XCircle,
} from "lucide-react";
import {
  DocumentExtraction,
  EntityReviewStatus,
  ExtractionEntity,
  MedicalDocument,
  TechnicalStatus,
} from "@/lib/types";
import {
  fetchDocumentExtraction,
  fetchExtractionEntities,
  getDocumentDownloadUrl,
  reviewExtractionEntity,
  triggerDocumentExtraction,
} from "@/lib/api";
import { formatBytes, formatDateTime } from "@/lib/utils";

interface ExtractionViewerModalProps {
  document: MedicalDocument | null;
  isOpen: boolean;
  onClose: () => void;
  onRefreshDocument?: () => void;
}

export function ExtractionViewerModal({
  document,
  isOpen,
  onClose,
  onRefreshDocument,
}: ExtractionViewerModalProps) {
  const [extraction, setExtraction] = useState<DocumentExtraction | null>(null);
  const [entities, setEntities] = useState<ExtractionEntity[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<ExtractionEntity | null>(null);
  const [filterReview, setFilterReview] = useState<string>("ALL");
  const [isRetrying, setIsRetrying] = useState<boolean>(false);

  // Edit entity modal state
  const [editingEntity, setEditingEntity] = useState<ExtractionEntity | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [editUnit, setEditUnit] = useState<string>("");
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);

  const loadExtractionData = async () => {
    if (!document) return;
    setLoading(true);
    setError(null);
    try {
      const ext = await fetchDocumentExtraction(document.id);
      setExtraction(ext);

      const entRes = await fetchExtractionEntities(document.id, {
        pageSize: 100,
        reviewStatus: filterReview !== "ALL" ? filterReview : undefined,
      });
      setEntities(entRes.items || []);
      if (entRes.items && entRes.items.length > 0 && !selectedEntity) {
        setSelectedEntity(entRes.items[0]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load extraction data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && document) {
      loadExtractionData();
    } else {
      setExtraction(null);
      setEntities([]);
      setSelectedEntity(null);
    }
  }, [isOpen, document?.id, filterReview]);

  if (!isOpen || !document) return null;

  const handleRetryExtraction = async () => {
    setIsRetrying(true);
    try {
      await triggerDocumentExtraction(document.id);
      setTimeout(() => {
        loadExtractionData();
        setIsRetrying(false);
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to trigger retry");
      setIsRetrying(false);
    }
  };

  const handleReviewAction = async (
    entityId: string,
    status: EntityReviewStatus,
    reviewedVal?: string,
    reviewedU?: string
  ) => {
    setSubmittingReview(true);
    try {
      await reviewExtractionEntity(
        document.id,
        entityId,
        status,
        reviewedVal,
        reviewedU
      );
      // Reload entities
      await loadExtractionData();
      if (onRefreshDocument) onRefreshDocument();
      setEditingEntity(null);
    } catch (err: any) {
      alert(err.message || "Failed to submit review");
    } finally {
      setSubmittingReview(false);
    }
  };

  const getStatusBadge = (status: TechnicalStatus) => {
    switch (status) {
      case "WITHIN_REPORTED_RANGE":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-800/80">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            Within Reported Range
          </span>
        );
      case "BELOW_REPORTED_RANGE":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-sky-950/80 text-sky-300 border border-sky-800/80">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
            Below Reported Range
          </span>
        );
      case "ABOVE_REPORTED_RANGE":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-rose-950/80 text-rose-300 border border-rose-800/80">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
            Above Reported Range
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
            Reported Range Unknown
          </span>
        );
    }
  };

  const downloadUrl = getDocumentDownloadUrl(document.id);
  const isPdf = document.mime_type === "application/pdf";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/85 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-7xl h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-slate-100">
                  Medical Document Extraction & Review Workbench
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                  {document.document_type}
                </span>
                {extraction && (
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                      extraction.status === "REVIEWED" || extraction.status === "EXTRACTED"
                        ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                        : extraction.status === "REVIEW_REQUIRED"
                        ? "bg-amber-950 text-amber-300 border border-amber-800"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    Status: {extraction.status}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {document.original_filename} • {formatBytes(document.file_size)} • Uploaded {formatDateTime(document.uploaded_at)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRetryExtraction}
              disabled={isRetrying}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? "animate-spin" : ""}`} />
              Re-extract
            </button>
            <a
              href={downloadUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              <Download className="w-3.5 h-3.5" />
              Download Original
            </a>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Workbench Body (Split View) */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 min-h-0 bg-slate-950/30">
          {/* Left: Original Document Preview (5 cols) */}
          <div className="lg:col-span-5 border-r border-slate-800 flex flex-col min-h-0 bg-slate-950/60">
            <div className="px-4 py-2.5 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400">
              <span className="font-medium text-slate-300">Original Document Preview</span>
              <span className="font-mono text-[10px]">
                SHA: {document.sha256_hash.substring(0, 12)}...
              </span>
            </div>

            <div className="flex-1 p-3 overflow-hidden flex flex-col items-center justify-center">
              {isPdf ? (
                <iframe
                  src={downloadUrl}
                  className="w-full h-full rounded-lg border border-slate-800 bg-slate-900 shadow-inner"
                  title="PDF Viewer"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center overflow-auto p-2 bg-slate-900/80 rounded-lg border border-slate-800">
                  <img
                    src={downloadUrl}
                    alt={document.original_filename}
                    className="max-w-full max-h-full object-contain rounded"
                  />
                </div>
              )}
            </div>

            {/* Source Provenance Info Box */}
            {selectedEntity && (
              <div className="p-4 border-t border-slate-800 bg-slate-900/70">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-medium text-sky-400 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    Source Provenance (Page {selectedEntity.page_number})
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    Confidence: {Math.round(selectedEntity.confidence * 100)}%
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950 border border-sky-900/30 text-xs font-mono text-sky-200 select-all">
                  "{selectedEntity.source_text || "Source line text unavailable"}"
                </div>
              </div>
            )}
          </div>

          {/* Right: Structured Clinical Entities & Review Workbench (7 cols) */}
          <div className="lg:col-span-7 flex flex-col min-h-0">
            {/* Filter and stats banner */}
            <div className="px-6 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
              <div className="flex items-center gap-2">
                <Filter className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-xs text-slate-400 font-medium">Filter Reviews:</span>
                <select
                  value={filterReview}
                  onChange={(e) => setFilterReview(e.target.value)}
                  className="px-2.5 py-1 text-xs rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500"
                >
                  <option value="ALL">All Extracted Parameters ({entities.length})</option>
                  <option value="PENDING">Pending Review</option>
                  <option value="ACCEPTED">Accepted / Verified</option>
                  <option value="EDITED">Clinician Edited</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </div>

              {extraction && (
                <div className="text-[11px] text-slate-400 font-mono">
                  Engine: <span className="text-slate-300">{extraction.provider}</span> • {extraction.processing_time_ms}ms
                </div>
              )}
            </div>

            {/* Content list */}
            <div className="flex-1 overflow-y-auto p-6 space-y-3">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-20 text-slate-400">
                  <RefreshCw className="w-8 h-8 animate-spin text-sky-400 mb-3" />
                  <p className="text-xs">Extracting structured clinical data from document...</p>
                </div>
              ) : error ? (
                <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-800/50 text-rose-300 text-xs flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <div>
                    <p className="font-semibold">Extraction Failed or Unavailable</p>
                    <p className="text-rose-400 mt-0.5">{error}</p>
                  </div>
                </div>
              ) : entities.length === 0 ? (
                <div className="text-center py-16 bg-slate-900/40 border border-slate-800 rounded-xl p-8">
                  <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs text-slate-300 font-medium">No laboratory entities detected</p>
                  <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
                    This document may not be a laboratory blood test, or the text extraction did not find recognizable clinical parameters.
                  </p>
                </div>
              ) : (
                entities.map((entity) => {
                  const isSelected = selectedEntity?.id === entity.id;
                  return (
                    <div
                      key={entity.id}
                      onClick={() => setSelectedEntity(entity)}
                      className={`p-4 rounded-xl border transition cursor-pointer ${
                        isSelected
                          ? "bg-slate-800/80 border-sky-500/80 shadow-lg shadow-sky-950/50 ring-1 ring-sky-500/50"
                          : "bg-slate-900/60 hover:bg-slate-800/40 border-slate-800/80"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-slate-100">
                              {entity.canonical_name}
                            </span>
                            {entity.raw_name !== entity.canonical_name && (
                              <span className="text-[11px] text-slate-500 font-mono">
                                (raw: "{entity.raw_name}")
                              </span>
                            )}
                            {getStatusBadge(entity.technical_status)}
                          </div>

                          <div className="flex items-baseline gap-2 mt-2">
                            <span className="text-xl font-bold font-mono text-slate-100 tracking-tight">
                              {entity.reviewed_value || entity.numeric_value || entity.value_text}
                            </span>
                            <span className="text-xs font-semibold text-sky-400">
                              {entity.normalized_unit || entity.original_unit || ""}
                            </span>
                            {entity.reference_range_text && (
                              <span className="text-[11px] text-slate-400 ml-3 font-mono">
                                Reported Ref: {entity.reference_range_text}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Review Actions & Confidence */}
                        <div className="flex flex-col items-end gap-2">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] text-slate-400 font-mono">
                              Extraction Conf:
                            </span>
                            <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-emerald-400 rounded-full"
                                style={{ width: `${Math.round(entity.confidence * 100)}%` }}
                              />
                            </div>
                            <span className="text-[10px] font-mono font-semibold text-slate-300">
                              {Math.round(entity.confidence * 100)}%
                            </span>
                          </div>

                          {/* Review status buttons */}
                          <div className="flex items-center gap-1.5 mt-1" onClick={(e) => e.stopPropagation()}>
                            {entity.review_status === "ACCEPTED" ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-950 text-emerald-300 border border-emerald-800">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Verified by Doctor
                              </span>
                            ) : entity.review_status === "EDITED" ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-sky-950 text-sky-300 border border-sky-800">
                                <Edit2 className="w-3.5 h-3.5" />
                                Doctor Edited ({entity.reviewed_value})
                              </span>
                            ) : entity.review_status === "REJECTED" ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-rose-950 text-rose-300 border border-rose-800">
                                <XCircle className="w-3.5 h-3.5" />
                                Rejected
                              </span>
                            ) : (
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleReviewAction(entity.id, "ACCEPTED")}
                                  disabled={submittingReview}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-900/60 hover:bg-emerald-800 text-emerald-200 border border-emerald-700/60 transition"
                                >
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  Accept
                                </button>
                                <button
                                  onClick={() => {
                                    setEditingEntity(entity);
                                    setEditValue(entity.value_text || "");
                                    setEditUnit(entity.normalized_unit || "");
                                  }}
                                  disabled={submittingReview}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                  Edit
                                </button>
                                <button
                                  onClick={() => handleReviewAction(entity.id, "REJECTED")}
                                  disabled={submittingReview}
                                  className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-800/60 transition"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Non-Diagnostic CDSS Footer Disclaimer */}
            <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center gap-3 text-xs text-slate-400">
              <Shield className="w-4 h-4 text-sky-400 flex-shrink-0" />
              <p className="leading-relaxed text-[11px]">
                <strong className="text-slate-300">CDSS Guardrail Notice:</strong> Extracted parameters reflect laboratory-reported numerical values only. Comparisons are technical checks against reported reference boundaries and do not constitute an automated medical diagnosis or clinical recommendation.
              </p>
            </div>
          </div>
        </div>

        {/* Edit Parameter Modal Dialog */}
        {editingEntity && (
          <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-md shadow-2xl">
              <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-sky-400" />
                Correct Extracted Value: {editingEntity.canonical_name}
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Original OCR detected: "{editingEntity.source_text}"
              </p>

              <div className="mt-4 space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Value
                  </label>
                  <input
                    type="text"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Unit
                  </label>
                  <input
                    type="text"
                    value={editUnit}
                    onChange={(e) => setEditUnit(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-sky-500"
                  />
                </div>
              </div>

              <div className="mt-6 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingEntity(null)}
                  disabled={submittingReview}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleReviewAction(
                      editingEntity.id,
                      "EDITED",
                      editValue,
                      editUnit
                    )
                  }
                  disabled={submittingReview}
                  className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition shadow-lg shadow-sky-950"
                >
                  {submittingReview ? "Saving..." : "Save Correction"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
