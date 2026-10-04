"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  Cpu,
  FileSpreadsheet,
  FileText,
  FileUp,
  FolderOpen,
  HeartPulse,
  Pill,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Users,
} from "lucide-react";
import { DocumentUploadModal } from "@/components/clinical/DocumentUploadModal";
import { MedicalDocumentsTable } from "@/components/clinical/MedicalDocumentsTable";
import { PatientTimeline } from "@/components/clinical/PatientTimeline";
import { DocumentType, MedicalDocument, Patient } from "@/lib/types";
import { deleteMedicalDocument, fetchPatientMedicalDocuments, fetchPatients } from "@/lib/api";

export default function ReportsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [documents, setDocuments] = useState<MedicalDocument[]>([]);
  const [selectedModality, setSelectedModality] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const patientList = await fetchPatients();
      setPatients(patientList);

      if (patientList.length > 0) {
        const targetPatient = selectedPatientId || patientList[0].id;
        if (!selectedPatientId) setSelectedPatientId(targetPatient);

        const docData = await fetchPatientMedicalDocuments(
          targetPatient,
          selectedModality === "ALL" ? undefined : selectedModality
        );
        setDocuments(docData.items);
      } else {
        setDocuments([]);
      }
    } catch (err) {
      console.error("Failed loading document ingestion hub data", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedPatientId, selectedModality]);

  const handleDelete = async (docId: string) => {
    try {
      await deleteMedicalDocument(docId);
      await loadData();
    } catch (err) {
      console.error("Failed deleting document", err);
    }
  };

  const filteredDocs = documents.filter((d) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      d.original_filename.toLowerCase().includes(q) ||
      d.sha256_hash.toLowerCase().includes(q) ||
      d.document_type.toLowerCase().includes(q)
    );
  });

  const selectedPatientObj = patients.find((p) => p.id === selectedPatientId);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-900 to-sky-950/40 p-6 rounded-2xl border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-tight">
              Medical Document Ingestion Hub
            </h1>
            <span className="text-xs bg-sky-500/20 text-sky-300 border border-sky-500/30 px-2 py-0.5 rounded-full font-mono font-medium">
              Phase 1 Verified
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Secure multi-modal intake pipeline: PDF, PNG, JPG, WEBP. Encrypted storage, server-side SHA-256 verification, and automated background preparation.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition flex items-center gap-1.5 border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setIsUploadOpen(true)}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-md shadow-sky-600/20"
          >
            <FileUp className="w-3.5 h-3.5" />
            <span>Ingest Document</span>
          </button>
        </div>
      </div>

      {/* Patient & Modality Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Patient Selection Dropdown */}
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-2">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-sky-400" />
            <span>Select Patient Dossier</span>
          </label>
          <select
            value={selectedPatientId}
            onChange={(e) => setSelectedPatientId(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
          >
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.mrn} — {p.first_name} {p.last_name}
              </option>
            ))}
          </select>
          {selectedPatientObj && (
            <p className="text-[11px] text-slate-400">
              DOB: {selectedPatientObj.date_of_birth} ({selectedPatientObj.gender}) • Blood: {selectedPatientObj.blood_group || "N/A"}
            </p>
          )}
        </div>

        {/* Search Field */}
        <div className="md:col-span-2 p-4 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-2">
          <label className="text-xs font-semibold text-slate-300">
            Filter Ingested Documents
          </label>
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by filename or SHA-256 hash..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>
            <select
              value={selectedModality}
              onChange={(e) => setSelectedModality(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="ALL">All Modalities</option>
              <option value="BLOOD_REPORT">Blood Reports (CBC, LFT)</option>
              <option value="PRESCRIPTION">Prescriptions (Rx)</option>
              <option value="XRAY">Chest / Skeletal X-Ray</option>
              <option value="SONOGRAPHY">Sonography (USG)</option>
              <option value="OTHER">Other Diagnostics</option>
              <option value="UNKNOWN">Unclassified (Unknown)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Modality Status Quick Badges */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
        <div
          onClick={() => setSelectedModality("BLOOD_REPORT")}
          className={`p-3 rounded-xl border cursor-pointer transition space-y-1 ${
            selectedModality === "BLOOD_REPORT"
              ? "bg-sky-950/60 border-sky-500"
              : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
          }`}
        >
          <div className="flex items-center gap-2 text-sky-400">
            <Activity className="w-4 h-4" />
            <span className="font-semibold text-slate-200">Blood Reports</span>
          </div>
          <p className="text-[10px] text-slate-400">Hematology, LFT, Lipid</p>
        </div>

        <div
          onClick={() => setSelectedModality("PRESCRIPTION")}
          className={`p-3 rounded-xl border cursor-pointer transition space-y-1 ${
            selectedModality === "PRESCRIPTION"
              ? "bg-teal-950/60 border-teal-500"
              : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
          }`}
        >
          <div className="flex items-center gap-2 text-teal-400">
            <Pill className="w-4 h-4" />
            <span className="font-semibold text-slate-200">Prescriptions</span>
          </div>
          <p className="text-[10px] text-slate-400">Rx Slips, Dosages</p>
        </div>

        <div
          onClick={() => setSelectedModality("XRAY")}
          className={`p-3 rounded-xl border cursor-pointer transition space-y-1 ${
            selectedModality === "XRAY"
              ? "bg-indigo-950/60 border-indigo-500"
              : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
          }`}
        >
          <div className="flex items-center gap-2 text-indigo-400">
            <Radio className="w-4 h-4" />
            <span className="font-semibold text-slate-200">Chest X-Rays</span>
          </div>
          <p className="text-[10px] text-slate-400">PA/AP Radiographs</p>
        </div>

        <div
          onClick={() => setSelectedModality("SONOGRAPHY")}
          className={`p-3 rounded-xl border cursor-pointer transition space-y-1 ${
            selectedModality === "SONOGRAPHY"
              ? "bg-rose-950/60 border-rose-500"
              : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
          }`}
        >
          <div className="flex items-center gap-2 text-rose-400">
            <HeartPulse className="w-4 h-4" />
            <span className="font-semibold text-slate-200">Sonography</span>
          </div>
          <p className="text-[10px] text-slate-400">Ultrasound Scans</p>
        </div>

        <div
          onClick={() => setSelectedModality("OTHER")}
          className={`p-3 rounded-xl border cursor-pointer transition space-y-1 ${
            selectedModality === "OTHER"
              ? "bg-amber-950/60 border-amber-500"
              : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
          }`}
        >
          <div className="flex items-center gap-2 text-amber-400">
            <FileSpreadsheet className="w-4 h-4" />
            <span className="font-semibold text-slate-200">Other Labs</span>
          </div>
          <p className="text-[10px] text-slate-400">General Diagnostics</p>
        </div>
      </div>

      {/* Documents Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">
            Ingested Medical Documents ({filteredDocs.length})
          </h2>
        </div>
        <MedicalDocumentsTable
          documents={filteredDocs}
          onRefresh={loadData}
          onDelete={handleDelete}
        />
      </div>

      {/* Phase 3: Patient Longitudinal Findings Timeline */}
      {selectedPatientId && (
        <div className="pt-2">
          <PatientTimeline patientId={selectedPatientId} />
        </div>
      )}

      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        patients={patients}
        preselectedPatientId={selectedPatientId}
        onUploadSuccess={loadData}
      />
    </div>
  );
}
