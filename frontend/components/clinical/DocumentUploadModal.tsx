"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  FileCheck,
  FileUp,
  Hash,
  Info,
  Loader2,
  RefreshCw,
  Search,
  UploadCloud,
  X,
} from "lucide-react";
import { DocumentType, DuplicateWarningInfo, Patient } from "@/lib/types";
import { uploadMedicalDocument } from "@/lib/api";

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  patients: Patient[];
  preselectedPatientId?: string;
  onUploadSuccess: () => void;
}

// Compute client-side SHA-256 hash using Web Crypto API
async function computeSHA256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function DocumentUploadModal({
  isOpen,
  onClose,
  patients,
  preselectedPatientId,
  onUploadSuccess,
}: DocumentUploadModalProps) {
  const [selectedPatientId, setSelectedPatientId] = useState(preselectedPatientId || patients[0]?.id || "");
  const [patientSearch, setPatientSearch] = useState("");
  const [docType, setDocType] = useState<DocumentType>("UNKNOWN");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [clientHash, setClientHash] = useState<string>("");
  const [isHashing, setIsHashing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [duplicateWarning, setDuplicateWarning] = useState<DuplicateWarningInfo | null>(null);
  const [successMsg, setSuccessMsg] = useState("");

  useEffect(() => {
    if (preselectedPatientId) {
      setSelectedPatientId(preselectedPatientId);
    } else if (patients.length > 0 && !selectedPatientId) {
      setSelectedPatientId(patients[0].id);
    }
  }, [preselectedPatientId, patients]);

  if (!isOpen) return null;

  const filteredPatients = patients.filter((p) => {
    const q = patientSearch.toLowerCase();
    return (
      p.mrn.toLowerCase().includes(q) ||
      p.first_name.toLowerCase().includes(q) ||
      p.last_name.toLowerCase().includes(q) ||
      (p.phone && p.phone.includes(q))
    );
  });

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setErrorMsg("");
      setDuplicateWarning(null);

      // Client-side size check (25 MB)
      if (file.size > 25 * 1024 * 1024) {
        setErrorMsg("Maximum allowed file size is 25 MB. Please select a smaller document.");
        setSelectedFile(null);
        setClientHash("");
        return;
      }

      // Check allowed extensions
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      const allowed = [".pdf", ".png", ".jpg", ".jpeg", ".webp"];
      if (!allowed.includes(ext)) {
        setErrorMsg(`Unsupported file type '${ext}'. Allowed: PDF, PNG, JPG, JPEG, WEBP.`);
        setSelectedFile(null);
        setClientHash("");
        return;
      }

      setSelectedFile(file);
      try {
        setIsHashing(true);
        const hash = await computeSHA256(file);
        setClientHash(hash);
      } catch (err) {
        console.warn("Could not compute client-side SHA256", err);
      } finally {
        setIsHashing(false);
      }
    }
  };

  const handleUpload = async (allowDuplicate: boolean = false) => {
    if (!selectedFile) {
      setErrorMsg("Please select a medical report or diagnostic image.");
      return;
    }
    if (!selectedPatientId) {
      setErrorMsg("Please select an authorized patient profile.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg("");

      const response = await uploadMedicalDocument(
        selectedPatientId,
        selectedFile,
        docType,
        allowDuplicate
      );

      if (response.duplicate_warning && !allowDuplicate) {
        setDuplicateWarning(response.duplicate_warning);
        setIsSubmitting(false);
        return;
      }

      setSuccessMsg("Document encrypted, verified, and queued for ingestion!");
      setTimeout(() => {
        onUploadSuccess();
        onClose();
        setSuccessMsg("");
        setSelectedFile(null);
        setClientHash("");
        setDuplicateWarning(null);
      }, 1000);
    } catch (err: any) {
      setErrorMsg(err.message || "Upload failed. Please verify network and patient authorization.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedPatientObj = patients.find((p) => p.id === selectedPatientId);

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center justify-center">
              <FileUp className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Ingest Medical Document</h3>
              <p className="text-xs text-slate-400">
                Encrypted server-side intake for PDF, PNG, JPG, and WEBP.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMsg && (
          <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-xl text-xs text-rose-300 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-200">Validation Error</p>
              <p className="mt-0.5">{errorMsg}</p>
            </div>
          </div>
        )}

        {successMsg && (
          <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-xl text-xs text-emerald-300 flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Duplicate Warning Prompt */}
        {duplicateWarning && (
          <div className="p-4 bg-amber-950/50 border border-amber-600/60 rounded-xl space-y-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-semibold text-amber-200">Duplicate Document Detected</h4>
                <p className="text-xs text-amber-300 mt-1 leading-relaxed">
                  {duplicateWarning.message}
                </p>
                <div className="mt-2 text-[11px] font-mono text-amber-400/80 bg-slate-950/60 p-2 rounded border border-amber-900/40">
                  SHA-256: {duplicateWarning.sha256_hash}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-amber-800/40 text-xs">
              <button
                type="button"
                onClick={() => setDuplicateWarning(null)}
                className="px-3 py-1.5 text-slate-300 hover:text-white rounded-lg hover:bg-slate-800 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleUpload(true)}
                disabled={isSubmitting}
                className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg font-medium transition flex items-center gap-1.5"
              >
                {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Proceed as Revision</span>
              </button>
            </div>
          </div>
        )}

        <div className="space-y-4 text-xs">
          {/* Patient Selection */}
          <div>
            <label className="block font-medium text-slate-300 mb-1.5">
              Select Patient <span className="text-rose-400">*</span>
            </label>
            <div className="space-y-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter by MRN or patient name..."
                  value={patientSearch}
                  onChange={(e) => setPatientSearch(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>
              <select
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-sky-500"
                required
              >
                {filteredPatients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.mrn} — {p.first_name} {p.last_name} ({p.gender}, DOB: {p.date_of_birth})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Modality Selector */}
          <div>
            <label className="block font-medium text-slate-300 mb-1.5">
              Document Modality
            </label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value as DocumentType)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="UNKNOWN">Auto Detect (Recommended — Deterministic Classifier)</option>
              <option value="BLOOD_REPORT">Blood / Hematology Report (CBC, Lipid, Metabolic)</option>
              <option value="PRESCRIPTION">Prescription / Medication Slip (Rx)</option>
              <option value="XRAY">Chest / Skeletal X-Ray (Radiograph)</option>
              <option value="SONOGRAPHY">Sonography / Ultrasound Scan (USG)</option>
              <option value="OTHER">Other Diagnostic Document</option>
            </select>
          </div>

          {/* Drag & Drop File Zone */}
          <div>
            <label className="block font-medium text-slate-300 mb-1.5">
              Medical Document File <span className="text-rose-400">*</span>
            </label>
            <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl p-6 text-center cursor-pointer transition bg-slate-950/40 relative">
              <input
                type="file"
                onChange={handleFileChange}
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />
              <FileUp className="w-8 h-8 text-sky-400 mx-auto mb-2" />
              <p className="font-medium text-slate-200">
                {selectedFile ? selectedFile.name : "Click or drag & drop medical document"}
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                Supported formats: PDF, PNG, JPG, JPEG, WEBP (Max 25 MB)
              </p>
            </div>
          </div>

          {/* Client SHA-256 Hash Display */}
          {selectedFile && (
            <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1.5">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span className="flex items-center gap-1 font-medium text-slate-300">
                  <Hash className="w-3 h-3 text-sky-400" />
                  Client SHA-256 Checksum:
                </span>
                <span className="font-mono text-[10px] text-slate-400">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                </span>
              </div>
              <p className="font-mono text-[10px] text-sky-400 break-all select-all">
                {isHashing ? "Calculating SHA-256 hash..." : clientHash || "Computing..."}
              </p>
            </div>
          )}
        </div>

        <div className="pt-3 flex items-center justify-between border-t border-slate-800">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <Info className="w-3.5 h-3.5 text-slate-400" />
            <span>Encrypted AES-256 at rest</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 transition"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => handleUpload(false)}
              disabled={isSubmitting || !selectedFile || !selectedPatientId}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition flex items-center gap-2 disabled:opacity-50 shadow-md shadow-sky-600/20"
            >
              {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{isSubmitting ? "Encrypting & Ingesting..." : "Ingest Document"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
