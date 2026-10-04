"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  Copy,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  HeartPulse,
  Info,
  Loader2,
  Pill,
  Radio,
  Sparkles,
  Trash2,
} from "lucide-react";
import { ClinicalAnalysis, DocumentType, MedicalDocument, ProcessingStatus } from "@/lib/types";
import { formatBytes, formatDateTime } from "@/lib/utils";
import { fetchDocumentStatus, getDocumentDownloadUrl, getClinicalAnalysis, triggerClinicalAnalysis } from "@/lib/api";
import { DocumentMetadataDrawer } from "./DocumentMetadataDrawer";
import { ExtractionViewerModal } from "./ExtractionViewerModal";
import { ClinicalInsightsPanel } from "./ClinicalInsightsPanel";

interface MedicalDocumentsTableProps {
  documents: MedicalDocument[];
  onRefresh?: () => void;
  onDelete?: (id: string) => void;
}

const modalityIcons: Record<DocumentType, any> = {
  BLOOD_REPORT: Activity,
  PRESCRIPTION: Pill,
  XRAY: Radio,
  SONOGRAPHY: HeartPulse,
  OTHER: FileSpreadsheet,
  UNKNOWN: FileText,
};

export function MedicalDocumentsTable({
  documents,
  onRefresh,
  onDelete,
}: MedicalDocumentsTableProps) {
  const [selectedDoc, setSelectedDoc] = useState<MedicalDocument | null>(null);
  const [extractionDoc, setExtractionDoc] = useState<MedicalDocument | null>(null);
  const [clinicalDoc, setClinicalDoc] = useState<MedicalDocument | null>(null);
  const [clinicalAnalysis, setClinicalAnalysis] = useState<ClinicalAnalysis | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [liveDocs, setLiveDocs] = useState<MedicalDocument[]>(documents);

  const handleOpenClinicalInsights = async (doc: MedicalDocument) => {
    setClinicalDoc(doc);
    try {
      setIsLoadingAnalysis(true);
      let analysis = await getClinicalAnalysis(doc.id);
      if (!analysis) {
        // Trigger initial analysis if not yet run
        analysis = await triggerClinicalAnalysis(doc.id, false);
      }
      setClinicalAnalysis(analysis);
    } catch (err) {
      console.error("Failed to load clinical analysis", err);
    } finally {
      setIsLoadingAnalysis(false);
    }
  };

  useEffect(() => {
    setLiveDocs(documents);
  }, [documents]);

  // Real-time status polling for queued or processing documents
  useEffect(() => {
    const pendingIds = liveDocs
      .filter((d) => d.processing_status === "QUEUED" || d.processing_status === "PROCESSING" || d.processing_status === "VALIDATING")
      .map((d) => d.id);

    if (pendingIds.length === 0) return;

    const interval = setInterval(async () => {
      let changed = false;
      const updatedList = await Promise.all(
        liveDocs.map(async (doc) => {
          if (doc.processing_status === "QUEUED" || doc.processing_status === "PROCESSING" || doc.processing_status === "VALIDATING") {
            try {
              const statusData = await fetchDocumentStatus(doc.id);
              if (statusData.processing_status !== doc.processing_status) {
                changed = true;
                return {
                  ...doc,
                  processing_status: statusData.processing_status,
                  document_type: statusData.document_type || doc.document_type,
                  page_count: statusData.page_count ?? doc.page_count,
                  metadata_json: statusData.metadata || doc.metadata_json,
                  processed_at: statusData.processed_at || doc.processed_at,
                };
              }
            } catch (err) {
              console.warn("Status poll error", err);
            }
          }
          return doc;
        })
      );

      if (changed) {
        setLiveDocs(updatedList);
        if (onRefresh) onRefresh();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [liveDocs, onRefresh]);

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 1500);
  };

  if (liveDocs.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-10 text-center space-y-2">
        <FileText className="w-10 h-10 text-slate-600 mx-auto" />
        <h4 className="text-xs font-semibold text-slate-300">No Medical Documents Ingested</h4>
        <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
          Upload diagnostic blood reports, prescriptions, X-rays, or sonograms to begin secure clinical ingestion.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/70 text-slate-400 font-medium border-b border-slate-800">
              <tr>
                <th className="px-4 py-3.5">Document / Modality</th>
                <th className="px-4 py-3.5">Format & Size</th>
                <th className="px-4 py-3.5">SHA-256 Checksum</th>
                <th className="px-4 py-3.5">Processing Pipeline</th>
                <th className="px-4 py-3.5">Uploaded</th>
                <th className="px-4 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {liveDocs.map((doc) => {
                const Icon = modalityIcons[doc.document_type] || FileText;
                const isPending =
                  doc.processing_status === "QUEUED" ||
                  doc.processing_status === "PROCESSING" ||
                  doc.processing_status === "VALIDATING";

                return (
                  <tr key={doc.id} className="hover:bg-slate-800/30 transition">
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-slate-800 border border-slate-700/60 text-sky-400 shrink-0">
                          <Icon className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-semibold text-slate-200 truncate max-w-xs">
                            {doc.original_filename}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700/50">
                              {doc.document_type.replace("_", " ")}
                            </span>
                            {doc.page_count ? (
                              <span className="text-[10px] text-slate-400">
                                {doc.page_count} pg
                              </span>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-3.5">
                      <p className="font-mono text-[11px] text-slate-300">
                        {formatBytes(doc.file_size)}
                      </p>
                      <p className="text-[10px] text-slate-500 font-mono">
                        {doc.mime_type.split("/")[1]?.toUpperCase()}
                      </p>
                    </td>

                    <td className="px-4 py-3.5">
                      <button
                        onClick={() => handleCopyHash(doc.sha256_hash)}
                        title="Click to copy full SHA-256 hash"
                        className="inline-flex items-center gap-1 font-mono text-[10px] text-slate-400 hover:text-sky-400 transition bg-slate-950 px-2 py-1 rounded border border-slate-800"
                      >
                        <span>{doc.sha256_hash.substring(0, 12)}...</span>
                        {copiedHash === doc.sha256_hash ? (
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3 text-slate-500" />
                        )}
                      </button>
                    </td>

                    <td className="px-4 py-3.5">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono font-medium ${
                          doc.processing_status === "COMPLETED"
                            ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                            : doc.processing_status === "FAILED" || doc.processing_status === "REJECTED"
                            ? "bg-rose-950 text-rose-300 border border-rose-800"
                            : "bg-sky-950 text-sky-300 border border-sky-800"
                        }`}
                      >
                        {isPending && <Loader2 className="w-2.5 h-2.5 animate-spin text-current" />}
                        <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                        {doc.processing_status}
                      </span>
                    </td>

                    <td className="px-4 py-3.5 text-slate-400 text-[11px]">
                      {formatDateTime(doc.created_at)}
                    </td>

                    <td className="px-4 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenClinicalInsights(doc)}
                          title="View Clinical Anomaly & Intelligence Findings (Phase 3)"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 hover:text-indigo-300 border border-indigo-500/30 transition text-[11px] font-semibold"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Clinical Insights</span>
                        </button>

                        <button
                          onClick={() => setExtractionDoc(doc)}
                          title="Inspect Extracted Medical Data & Clinician Review"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 hover:text-sky-300 border border-sky-500/30 transition text-[11px] font-medium"
                        >
                          <Activity className="w-3.5 h-3.5" />
                          <span>Review Data</span>
                        </button>

                        <button
                          onClick={() => setSelectedDoc(doc)}
                          title="View Ingestion Metadata"
                          className="p-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>

                        <a
                          href={getDocumentDownloadUrl(doc.id)}
                          target="_blank"
                          rel="noreferrer"
                          title="Secure Stream / Download"
                          className="p-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>

                        {onDelete && (
                          <button
                            onClick={() => onDelete(doc.id)}
                            title="Soft Delete Document"
                            className="p-1.5 rounded-lg bg-slate-800/60 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 transition"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <DocumentMetadataDrawer
        document={selectedDoc}
        onClose={() => setSelectedDoc(null)}
        onDelete={onDelete}
      />

      <ExtractionViewerModal
        document={extractionDoc}
        isOpen={!!extractionDoc}
        onClose={() => setExtractionDoc(null)}
        onRefreshDocument={onRefresh}
      />

      {/* Phase 3 Clinical Insights Modal */}
      {clinicalDoc && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 overflow-hidden">
          <div className="w-full max-w-6xl h-[90vh] flex flex-col">
            <ClinicalInsightsPanel
              documentId={clinicalDoc.id}
              analysis={clinicalAnalysis}
              onAnalysisUpdate={(updated) => setClinicalAnalysis(updated)}
              onClose={() => {
                setClinicalDoc(null);
                setClinicalAnalysis(null);
              }}
            />
          </div>
        </div>
      )}
    </>
  );
}

