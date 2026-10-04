"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  Cpu,
  FileSpreadsheet,
  FileUp,
  HeartPulse,
  Pill,
  Plus,
  Radio,
  RefreshCw,
  ShieldCheck,
  UserPlus,
} from "lucide-react";
import { MetricsOverview } from "@/components/clinical/MetricsOverview";
import { DocumentUploadModal } from "@/components/clinical/DocumentUploadModal";
import { RecentReportsTable } from "@/components/clinical/RecentReportsTable";
import { PatientList } from "@/components/clinical/PatientList";
import { SystemHealthCard } from "@/components/clinical/SystemHealthCard";
import { Patient, Report, SystemHealth } from "@/lib/types";
import { fetchHealth, fetchPatients, fetchRecentReports, createPatient } from "@/lib/api";

export default function DashboardPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isCreatingPatient, setIsCreatingPatient] = useState(false);

  // Initial mock sample data for Phase 0 demonstration if DB empty
  const loadData = async () => {
    try {
      setIsLoading(true);
      const [hData, pData, rData] = await Promise.allSettled([
        fetchHealth(),
        fetchPatients(),
        fetchRecentReports(),
      ]);

      if (hData.status === "fulfilled") setHealth(hData.value);
      if (pData.status === "fulfilled") setPatients(pData.value);
      if (rData.status === "fulfilled") setReports(rData.value);
    } catch (e) {
      console.error("Failed loading dashboard data", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateSamplePatient = async () => {
    try {
      setIsCreatingPatient(true);
      const sample = {
        mrn: `MRN-2026-${Math.floor(1000 + Math.random() * 9000)}`,
        first_name: "Eleanor",
        last_name: "Vance",
        date_of_birth: "1988-04-14",
        gender: "female",
        blood_group: "O+",
        phone: "+1-555-0199",
        email: "e.vance@example.org",
        known_allergies: ["Penicillin", "Sulfa"],
        chronic_conditions: ["Hypothyroidism", "Mild Asthma"],
      };
      await createPatient(sample);
      await loadData();
    } catch (err) {
      console.error("Failed creating patient", err);
    } finally {
      setIsCreatingPatient(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-900 to-sky-950/40 p-6 rounded-2xl border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
              Clinical Decision-Support Dashboard
            </h1>
            <span className="text-xs bg-sky-500/20 text-sky-300 border border-sky-500/30 px-2 py-0.5 rounded-full font-mono font-medium">
              Phase 0 Foundation
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Assistive platform for structured extraction, lab value normalization, and multi-modal clinical ingestion.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition flex items-center gap-1.5 border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleCreateSamplePatient}
            disabled={isCreatingPatient}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-sky-400 rounded-lg text-xs font-medium transition flex items-center gap-1.5 border border-sky-900/50"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>{isCreatingPatient ? "Creating..." : "Seed Patient"}</span>
          </button>
          <button
            onClick={() => setIsUploadOpen(true)}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-lg shadow-sky-600/20"
          >
            <FileUp className="w-3.5 h-3.5" />
            <span>Ingest Document</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <MetricsOverview
        totalPatients={patients.length}
        totalReports={reports.length}
        pendingJobs={0}
        abnormalitiesFlagged={14}
      />

      {/* Two Column Layout: Ingestion Table & Patient Directory */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Ingested Documents */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Recent Ingestion Queue</h2>
              <p className="text-[11px] text-slate-400">
                Encrypted multi-modal medical document uploads & extraction state
              </p>
            </div>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Upload New</span>
            </button>
          </div>
          <RecentReportsTable reports={reports} onRefresh={loadData} />
        </div>

        {/* Right Column: Patients Directory & System Health */}
        <div className="space-y-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">Patients Under Review</h2>
                <p className="text-[11px] text-slate-400">Longitudinal clinical records</p>
              </div>
            </div>
            <PatientList patients={patients.slice(0, 4)} />
          </div>

          <SystemHealthCard health={health} />
        </div>
      </div>

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        patients={patients}
        onUploadSuccess={loadData}
      />
    </div>
  );
}
