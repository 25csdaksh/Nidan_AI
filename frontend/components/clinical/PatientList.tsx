import React from "react";
import Link from "next/link";
import { AlertTriangle, ChevronRight, Droplet, User, Users } from "lucide-react";
import { Patient } from "@/lib/types";
import { formatDate } from "@/lib/utils";

interface PatientListProps {
  patients: Patient[];
}

export function PatientList({ patients }: PatientListProps) {
  if (patients.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 text-center">
        <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <p className="text-xs text-slate-300 font-medium">No patient records found</p>
        <p className="text-[11px] text-slate-500 mt-1">
          Add a patient record to start tracking clinical longitudinal history.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {patients.map((patient) => (
        <div
          key={patient.id}
          className="p-3.5 bg-slate-900/70 border border-slate-800/80 hover:border-slate-700 rounded-xl transition flex items-center justify-between group"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold text-slate-300">
              {patient.first_name[0]}
              {patient.last_name[0]}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-200 text-xs">
                  {patient.first_name} {patient.last_name}
                </span>
                <span className="text-[10px] bg-slate-800 font-mono text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">
                  {patient.mrn}
                </span>
                {patient.blood_group && (
                  <span className="text-[10px] bg-rose-950/60 text-rose-300 font-medium px-1.5 py-0.5 rounded border border-rose-800/50 flex items-center gap-1">
                    <Droplet className="w-2.5 h-2.5" />
                    {patient.blood_group}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-0.5">
                <span className="capitalize">{patient.gender}</span>
                <span>•</span>
                <span>DOB: {formatDate(patient.date_of_birth)}</span>
                {patient.known_allergies.length > 0 && (
                  <>
                    <span>•</span>
                    <span className="text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      {patient.known_allergies.join(", ")}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          <Link
            href={`/patients?id=${patient.id}`}
            className="text-xs text-sky-400 group-hover:text-sky-300 flex items-center gap-1 font-medium transition"
          >
            <span>Review History</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ))}
    </div>
  );
}
