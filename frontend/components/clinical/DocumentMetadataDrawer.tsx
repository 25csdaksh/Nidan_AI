"use client";

import React from "react";
import {
  Activity,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  FileSpreadsheet,
  FileText,
  HardDrive,
  Hash,
  HeartPulse,
  Layers,
  Pill,
  Radio,
  Shield,
  Trash2,
  User,
  X,
} from "lucide-react";
import { DocumentType, MedicalDocument } from "@/lib/types";
import { formatBytes, formatDateTime } from "@/lib/utils";
import { getDocumentDownloadUrl } from "@/lib/api";

interface DocumentMetadataDrawerProps {
  document: MedicalDocument | null;
  onClose: () => void;
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

export function DocumentMetadataDrawer({
  document,
  onClose,
  onDelete,
}: DocumentMetadataDrawerProps) {
  if (!document) return null;

  const Icon = modalityIcons[document.document_type] || FileText;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 max-h-[90vh] overflow-y-auto text-xs">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white leading-tight">
                {document.original_filename}
              </h3>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">ID: {document.id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Primary Meta Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
          <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800">
            <p className="text-[10px] text-slate-500">Modality</p>
            <p className="font-semibold text-slate-200 mt-0.5">
              {document.document_type.replace("_", " ")}
            </p>
          </div>
          <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800">
            <p className="text-[10px] text-slate-500">File Size</p>
            <p className="font-semibold text-slate-200 mt-0.5 font-mono">
              {formatBytes(document.file_size)}
            </p>
          </div>
          <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800">
            <p className="text-[10px] text-slate-500">Pages / Dimensions</p>
            <p className="font-semibold text-slate-200 mt-0.5">
              {document.page_count
                ? `${document.page_count} Pages`
                : document.metadata_json?.image_width
                ? `${document.metadata_json.image_width}x${document.metadata_json.image_height}`
                : "1 Page"}
            </p>
          </div>
          <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800">
            <p className="text-[10px] text-slate-500">Status</p>
            <p className="font-semibold text-emerald-400 mt-0.5 font-mono">
              {document.processing_status}
            </p>
          </div>
        </div>

        {/* Security & Storage Details */}
        <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2">
          <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
            <Shield className="w-3.5 h-3.5 text-sky-400" />
            <span>Cryptographic Integrity & Storage Key</span>
          </div>

          <div className="space-y-1.5 text-[11px]">
            <div>
              <span className="text-slate-500 block">Server-Side SHA-256 Hash:</span>
              <p className="font-mono text-[10px] text-sky-400 break-all select-all bg-slate-900/90 p-1.5 rounded border border-slate-800">
                {document.sha256_hash}
              </p>
            </div>
            <div>
              <span className="text-slate-500 block">Encrypted Storage Key (Internal UUID):</span>
              <p className="font-mono text-[10px] text-slate-300 break-all bg-slate-900/90 p-1.5 rounded border border-slate-800">
                {document.storage_key}
              </p>
            </div>
          </div>
        </div>

        {/* Structural Metadata from Ingestion Worker */}
        {document.metadata_json && Object.keys(document.metadata_json).length > 0 && (
          <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
              <Layers className="w-3.5 h-3.5 text-teal-400" />
              <span>Extracted Structural Metrics</span>
            </div>
            <pre className="p-2.5 bg-slate-900 rounded-lg text-[10px] font-mono text-slate-300 overflow-x-auto border border-slate-800 max-h-36">
              {JSON.stringify(document.metadata_json, null, 2)}
            </pre>
          </div>
        )}

        {/* Action Controls */}
        <div className="pt-2 flex items-center justify-between border-t border-slate-800">
          {onDelete ? (
            <button
              onClick={() => {
                if (confirm("Are you sure you want to soft delete this medical document?")) {
                  onDelete(document.id);
                  onClose();
                }
              }}
              className="text-rose-400 hover:text-rose-300 flex items-center gap-1 font-medium transition"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete Document</span>
            </button>
          ) : (
            <div></div>
          )}

          <div className="flex items-center gap-2">
            <a
              href={getDocumentDownloadUrl(document.id)}
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg font-medium transition flex items-center gap-1.5 shadow-md shadow-sky-600/20"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Secure Stream / View</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
