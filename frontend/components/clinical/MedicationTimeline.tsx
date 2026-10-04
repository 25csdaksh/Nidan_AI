"use client";

import React from "react";
import { PatientMedicationTimeline } from "@/lib/types";
import {
  Calendar,
  Pill,
  ShieldAlert,
  User,
  Clock,
  CheckCircle2,
  ChevronRight,
  FileText,
} from "lucide-react";

interface MedicationTimelineProps {
  timeline: PatientMedicationTimeline;
  onSelectPrescription?: (prescriptionId: string) => void;
}

export const MedicationTimeline: React.FC<MedicationTimelineProps> = ({
  timeline,
  onSelectPrescription,
}) => {
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "Unknown Date";
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

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-5 border-b border-slate-800">
        <div>
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Clock className="w-5 h-5 text-cyan-400" />
            Longitudinal Medication Timeline
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Chronological overview of documented prescriptions and active medications across visits.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs bg-slate-950 px-3.5 py-1.5 rounded-lg border border-slate-800">
          <span className="text-slate-400">Total Encounters: <b className="text-slate-200">{timeline.total_prescriptions}</b></span>
          <span className="text-slate-600">•</span>
          <span className="text-slate-400">Medications: <b className="text-cyan-300">{timeline.total_medications}</b></span>
        </div>
      </div>

      {/* Active Medications Summary Chips */}
      {timeline.active_medications_summary && timeline.active_medications_summary.length > 0 && (
        <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800 space-y-2">
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block flex items-center gap-1.5">
            <Pill className="w-3.5 h-3.5 text-emerald-400" />
            Active / Documented Drug Regimen ({timeline.active_medications_summary.length})
          </span>
          <div className="flex flex-wrap gap-2 pt-1">
            {timeline.active_medications_summary.map((medName, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 bg-slate-900 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700/80 flex items-center gap-1.5 shadow-sm"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                {medName}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Chronological Timeline Events */}
      <div className="space-y-4 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800">
        {timeline.events.map((event, idx) => (
          <div key={event.prescription_id || idx} className="relative flex items-start gap-4 pl-1">
            {/* Timeline Dot */}
            <div className="w-7 h-7 rounded-full bg-slate-900 border-2 border-cyan-500 flex items-center justify-center text-cyan-400 flex-shrink-0 z-10 shadow">
              <Calendar className="w-3.5 h-3.5" />
            </div>

            {/* Event Card */}
            <div className="bg-slate-950/80 border border-slate-800 hover:border-slate-700 p-4 rounded-xl flex-1 transition space-y-3 shadow-sm">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-2 border-b border-slate-800/80">
                <div>
                  <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    {formatDate(event.prescription_date)}
                    {event.prescriber_name && (
                      <span className="text-xs font-normal text-slate-400">
                        • Prescribed by <span className="text-slate-300 font-medium">{event.prescriber_name}</span>
                      </span>
                    )}
                  </h4>
                </div>

                <div className="flex items-center gap-2">
                  {event.safety_alert_count > 0 && (
                    <span className="px-2 py-0.5 bg-amber-950/80 text-amber-300 text-[11px] font-bold rounded border border-amber-700/50 flex items-center gap-1">
                      <ShieldAlert className="w-3 h-3 text-amber-400" />
                      {event.safety_alert_count} Alert{event.safety_alert_count > 1 ? "s" : ""}
                    </span>
                  )}
                  {onSelectPrescription && (
                    <button
                      onClick={() => onSelectPrescription(event.prescription_id)}
                      className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1"
                    >
                      View Details <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Medication Chips in this Event */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {event.medications.map((m) => (
                  <div
                    key={m.id}
                    className="bg-slate-900/90 p-2.5 rounded-lg border border-slate-800 flex justify-between items-center text-xs"
                  >
                    <div>
                      <span className="font-bold text-slate-200">
                        {m.canonical_medication_name !== "UNKNOWN"
                          ? m.canonical_medication_name
                          : m.raw_medication_name}
                      </span>
                      <span className="text-[11px] text-slate-400 block">
                        {m.strength_value ? `${m.strength_value} ${m.strength_unit || ""}` : ""} {m.frequency_code ? `• ${m.frequency_code}` : ""}
                      </span>
                    </div>

                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        m.confidence >= 0.85 ? "text-emerald-400" : "text-amber-400"
                      }`}
                    >
                      {Math.round(m.confidence * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
