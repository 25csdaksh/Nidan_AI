import React from "react";
import { Activity, Download, Eye, FileText, HeartPulse, Pill, Radio } from "lucide-react";
import { DocumentType, MedicalDocument } from "@/lib/types";
import { formatBytes, formatDateTime } from "@/lib/utils";

interface RecentReportsTableProps {
  reports: MedicalDocument[];
  onRefresh?: () => void;
}

const modalityIcons: Record<DocumentType, any> = {
  BLOOD_REPORT: Activity,
  PRESCRIPTION: Pill,
  XRAY: Radio,
  SONOGRAPHY: HeartPulse,
  OTHER: FileText,
  UNKNOWN: FileText,
};

export function RecentReportsTable({ reports }: RecentReportsTableProps) {
  if (reports.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 text-center">
        <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <p className="text-xs text-slate-300 font-medium">No medical documents uploaded yet</p>
        <p className="text-[11px] text-slate-500 mt-1">
          Upload blood reports, prescriptions, X-rays or sonographies to begin.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/60 text-slate-400 font-medium border-b border-slate-800">
            <tr>
              <th className="px-4 py-3">Document / File</th>
              <th className="px-4 py-3">Modality</th>
              <th className="px-4 py-3">SHA-256 Checksum</th>
              <th className="px-4 py-3">Pipeline Status</th>
              <th className="px-4 py-3">Uploaded</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {reports.map((report) => {
              const Icon = modalityIcons[report.document_type] || FileText;
              return (
                <tr key={report.id} className="hover:bg-slate-800/30 transition">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-lg bg-slate-800 text-sky-400">
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-200">{report.original_filename}</p>
                        <p className="text-[10px] text-slate-500 font-mono">
                          {formatBytes(report.file_size)}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="capitalize px-2 py-0.5 rounded text-[11px] bg-slate-800 text-slate-300 border border-slate-700/50">
                      {report.document_type.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-[10px] text-slate-500">
                    {report.sha256_hash.substring(0, 16)}...
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                        report.processing_status === "COMPLETED" || report.processing_status === "STORED"
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                          : report.processing_status === "PROCESSING" || report.processing_status === "QUEUED"
                          ? "bg-sky-950 text-sky-300 border border-sky-800 animate-pulse"
                          : report.processing_status === "FAILED" || report.processing_status === "REJECTED"
                          ? "bg-rose-950 text-rose-300 border border-rose-800"
                          : "bg-amber-950 text-amber-300 border border-amber-800"
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                      {report.processing_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-[11px]">
                    {formatDateTime(report.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        title="View Metadata"
                        className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

