"use client";

import React, { useState } from "react";
import {
  Prescription,
  PrescriptionMedication,
  MedicationSafetyFinding,
} from "@/lib/types";
import {
  Pill,
  AlertTriangle,
  FileText,
  User,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  ShieldAlert,
  ChevronRight,
  Info,
} from "lucide-react";

interface PrescriptionViewerProps {
  prescription: Prescription;
  onSelectMedication?: (med: PrescriptionMedication) => void;
  onSelectFinding?: (finding: MedicationSafetyFinding) => void;
  onRunSafetyCheck?: () => void;
  isAnalyzing?: boolean;
}

export const PrescriptionViewer: React.FC<PrescriptionViewerProps> = ({
  prescription,
  onSelectMedication,
  onSelectFinding,
  onRunSafetyCheck,
  isAnalyzing = false,
}) => {
  const [selectedMed, setSelectedMed] = useState<PrescriptionMedication | null>(null);

  const formatPrescriptionDate = (dateStr?: string) => {
    if (!dateStr) return "Unknown / Not Documented";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
      case "EXTRACTED":
        return <span className="px-2.5 py-1 bg-emerald-950/80 text-emerald-300 text-xs font-semibold rounded-full border border-emerald-700/50 flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5" /> Active Record</span>;
      case "REVIEW_REQUIRED":
        return <span className="px-2.5 py-1 bg-amber-950/80 text-amber-300 text-xs font-semibold rounded-full border border-amber-700/50 flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" /> Review Required</span>;
      case "DISCONTINUED":
      case "COMPLETED":
        return <span className="px-2.5 py-1 bg-slate-800 text-slate-300 text-xs font-semibold rounded-full border border-slate-700 flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> {status}</span>;
      default:
        return <span className="px-2.5 py-1 bg-slate-800 text-slate-300 text-xs font-semibold rounded-full border border-slate-700">{status}</span>;
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
      case "HIGH":
        return <span className="px-2 py-0.5 bg-rose-950/80 text-rose-300 text-xs font-semibold rounded border border-rose-700/50 flex items-center gap-1"><ShieldAlert className="w-3 h-3 text-rose-400" /> {sev}</span>;
      case "MODERATE":
        return <span className="px-2 py-0.5 bg-amber-950/80 text-amber-300 text-xs font-semibold rounded border border-amber-700/50 flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-amber-400" /> {sev}</span>;
      default:
        return <span className="px-2 py-0.5 bg-blue-950/80 text-blue-300 text-xs font-semibold rounded border border-blue-700/50 flex items-center gap-1"><Info className="w-3 h-3 text-blue-400" /> {sev}</span>;
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-5 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-cyan-950/80 text-cyan-400 border border-cyan-700/50 rounded-lg">
              <Pill className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                Prescription Record
                {getStatusBadge(prescription.status)}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Prescription ID: <code className="text-slate-300">{prescription.id.slice(0, 8)}</code> • Extraction Confidence: <span className="font-semibold text-cyan-300">{Math.round(prescription.source_confidence * 100)}%</span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end sm:self-auto">
          {onRunSafetyCheck && (
            <button
              onClick={onRunSafetyCheck}
              disabled={isAnalyzing}
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg shadow transition flex items-center gap-2 disabled:opacity-50"
            >
              <ShieldAlert className="w-4 h-4" />
              {isAnalyzing ? "Evaluating Safety..." : "Run Safety Check"}
            </button>
          )}
        </div>
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-950/60 p-4 rounded-lg border border-slate-800/80 text-xs">
        <div className="flex items-center gap-2.5 text-slate-300">
          <Calendar className="w-4 h-4 text-slate-400" />
          <div>
            <span className="text-slate-500 block">Date of Prescription</span>
            <span className="font-medium text-slate-200">{formatPrescriptionDate(prescription.prescription_date)}</span>
          </div>
        </div>
        <div className="flex items-center gap-2.5 text-slate-300">
          <User className="w-4 h-4 text-slate-400" />
          <div>
            <span className="text-slate-500 block">Documented Prescriber</span>
            <span className="font-medium text-slate-200">{prescription.prescriber_name || "Not Documented"}</span>
          </div>
        </div>
        <div className="flex items-center gap-2.5 text-slate-300">
          <FileText className="w-4 h-4 text-slate-400" />
          <div>
            <span className="text-slate-500 block">Source Document</span>
            <span className="font-mono text-cyan-400">
              {prescription.document_id ? `${prescription.document_id.slice(0, 8)}...` : "Manual Entry"}
            </span>
          </div>
        </div>
      </div>

      {/* Medication List Table */}
      <div>
        <div className="flex justify-between items-center mb-3">
          <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Pill className="w-4 h-4 text-cyan-400" />
            Prescribed Medications ({prescription.medications.length})
          </h4>
        </div>

        {prescription.medications.length === 0 ? (
          <div className="bg-slate-950/40 border border-slate-800/60 rounded-lg p-6 text-center text-sm text-slate-400">
            No medication entries detected or recorded for this prescription.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800 font-semibold">
                <tr>
                  <th className="px-4 py-3">Medication</th>
                  <th className="px-4 py-3">Strength / Form</th>
                  <th className="px-4 py-3">Route</th>
                  <th className="px-4 py-3">Frequency</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3 text-right">Review Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70 bg-slate-900/40">
                {prescription.medications.map((med) => {
                  const isSelected = selectedMed?.id === med.id;
                  return (
                    <tr
                      key={med.id}
                      onClick={() => {
                        setSelectedMed(med);
                        onSelectMedication?.(med);
                      }}
                      className={`hover:bg-slate-800/60 cursor-pointer transition ${
                        isSelected ? "bg-cyan-950/30 border-l-2 border-cyan-400" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        <div className="font-bold text-slate-100 flex items-center gap-1.5">
                          {med.canonical_medication_name !== "UNKNOWN"
                            ? med.canonical_medication_name
                            : med.raw_medication_name}
                          {med.is_prn && (
                            <span className="px-1.5 py-0.2 bg-amber-950 text-amber-300 text-[10px] rounded border border-amber-800/60">
                              PRN
                            </span>
                          )}
                        </div>
                        {med.generic_name && (
                          <span className="text-[11px] text-slate-400 block">{med.generic_name}</span>
                        )}
                        {med.raw_medication_name && med.raw_medication_name !== med.canonical_medication_name && (
                          <span className="text-[10px] text-slate-500 font-mono block">Raw: {med.raw_medication_name}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-200">
                        {med.strength_value ? `${med.strength_value} ${med.strength_unit || ""}` : "—"}
                        {med.dosage_form && (
                          <span className="text-[11px] text-slate-400 block">{med.dosage_form}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-300">
                        {med.route || <span className="text-slate-500 italic">Unspecified</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-semibold text-cyan-300">{med.frequency_code || "—"}</span>
                        {med.frequency_text && (
                          <span className="text-[11px] text-slate-400 block">{med.frequency_text}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-300">
                        {med.duration_value ? `${med.duration_value} ${med.duration_unit || "DAYS"}` : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`font-semibold ${
                            med.confidence >= 0.85
                              ? "text-emerald-400"
                              : med.confidence >= 0.70
                              ? "text-amber-400"
                              : "text-rose-400"
                          }`}
                        >
                          {Math.round(med.confidence * 100)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                            med.review_status === "ACCEPTED"
                              ? "bg-emerald-950/80 text-emerald-300 border-emerald-700/50"
                              : med.review_status === "MODIFIED"
                              ? "bg-blue-950/80 text-blue-300 border-blue-700/50"
                              : med.review_status === "REJECTED"
                              ? "bg-rose-950/80 text-rose-300 border-rose-700/50"
                              : "bg-slate-800 text-slate-300 border-slate-700"
                          }`}
                        >
                          {med.review_status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Safety Findings Alert Banner if any exist */}
      {prescription.safety_findings && prescription.safety_findings.length > 0 && (
        <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            Safety Observations ({prescription.safety_findings.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {prescription.safety_findings.map((f) => (
              <div
                key={f.id}
                onClick={() => onSelectFinding?.(f)}
                className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 p-3.5 rounded-lg cursor-pointer transition space-y-1.5"
              >
                <div className="flex justify-between items-start gap-2">
                  <span className="text-xs font-bold text-slate-200 leading-snug">{f.title}</span>
                  {getSeverityBadge(f.severity)}
                </div>
                <p className="text-xs text-slate-400 line-clamp-2">{f.description}</p>
                <div className="text-[11px] text-cyan-400 flex items-center gap-1 pt-1 font-medium">
                  View evidence & clinician correlation <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
