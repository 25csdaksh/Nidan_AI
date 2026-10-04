"use client";

import React, { useEffect, useState } from "react";
import {
  Patient,
  Prescription,
  MedicationSafetyFinding,
  PatientMedicationTimeline,
  MedicationReviewStatus,
} from "@/lib/types";
import {
  fetchPatients,
  getPatientPrescriptions,
  getPatientMedicationSafetyFindings,
  getPatientMedicationTimeline,
  runMedicationSafetyAnalysis,
  reviewMedicationSafetyFinding,
} from "@/lib/api";
import { Header } from "@/components/clinical/Header";
import { Sidebar } from "@/components/clinical/Sidebar";
import { DisclaimerBanner } from "@/components/clinical/DisclaimerBanner";
import { PrescriptionViewer } from "@/components/clinical/PrescriptionViewer";
import { MedicationSafetyPanel } from "@/components/clinical/MedicationSafetyPanel";
import { MedicationTimeline } from "@/components/clinical/MedicationTimeline";
import { MedicationReviewModal } from "@/components/clinical/MedicationReviewModal";
import {
  Pill,
  ShieldAlert,
  Clock,
  User,
  Activity,
  Layers,
  Sparkles,
  RefreshCw,
  Search,
} from "lucide-react";

export default function PrescriptionsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [selectedPrescription, setSelectedPrescription] = useState<Prescription | null>(null);
  const [safetyFindings, setSafetyFindings] = useState<MedicationSafetyFinding[]>([]);
  const [timeline, setTimeline] = useState<PatientMedicationTimeline | null>(null);
  const [reviewingFinding, setReviewingFinding] = useState<MedicationSafetyFinding | null>(null);

  const [activeTab, setActiveTab] = useState<"prescriptions" | "safety" | "timeline">("prescriptions");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    loadPatients();
  }, []);

  useEffect(() => {
    if (selectedPatient) {
      loadPatientData(selectedPatient.id);
    }
  }, [selectedPatient]);

  const loadPatients = async () => {
    try {
      setIsLoading(true);
      const data = await fetchPatients();
      setPatients(data);
      if (data.length > 0 && !selectedPatient) {
        setSelectedPatient(data[0]);
      }
    } catch (err) {
      console.error("Failed to load patients", err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadPatientData = async (patientId: string) => {
    try {
      setIsLoading(true);
      const [rxs, findings, timelineData] = await Promise.all([
        getPatientPrescriptions(patientId).catch(() => []),
        getPatientMedicationSafetyFindings(patientId).catch(() => []),
        getPatientMedicationTimeline(patientId).catch(() => null),
      ]);

      setPrescriptions(rxs);
      setSafetyFindings(findings);
      setTimeline(timelineData);
      if (rxs.length > 0) {
        setSelectedPrescription(rxs[0]);
      } else {
        setSelectedPrescription(null);
      }
    } catch (err) {
      console.error("Failed to load patient prescription details", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunSafetyCheck = async () => {
    if (!selectedPatient) return;
    try {
      setIsAnalyzing(true);
      await runMedicationSafetyAnalysis(selectedPatient.id);
      await loadPatientData(selectedPatient.id);
    } catch (err) {
      console.error("Safety check failed", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSubmitReview = async (
    findingId: string,
    reviewStatus: MedicationReviewStatus,
    clinicianNote: string
  ) => {
    await reviewMedicationSafetyFinding(findingId, {
      review_status: reviewStatus,
      clinician_note: clinicianNote,
    });
    if (selectedPatient) {
      await loadPatientData(selectedPatient.id);
    }
  };

  const filteredPatients = patients.filter((p) => {
    const fullName = `${p.first_name} ${p.last_name}`.toLowerCase();
    const mrn = p.mrn.toLowerCase();
    const q = searchQuery.toLowerCase();
    return fullName.includes(q) || mrn.includes(q);
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <DisclaimerBanner />

      <div className="flex-1 flex flex-col md:flex-row">
        <Sidebar />

        <main className="flex-1 p-6 space-y-6 max-w-7xl mx-auto w-full">
          {/* Top Title Banner */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/90 border border-slate-800 p-6 rounded-2xl shadow-xl">
            <div>
              <h1 className="text-2xl font-black text-slate-100 flex items-center gap-3">
                <div className="p-2 bg-cyan-950 border border-cyan-700/60 rounded-xl text-cyan-400">
                  <Pill className="w-6 h-6" />
                </div>
                Prescription Intelligence & Medication Safety
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Deterministic medication extraction, drug interaction alerts, allergy screening, and longitudinal regimen tracking (CDSS Level 1 & 2).
              </p>
            </div>

            {selectedPatient && (
              <div className="flex items-center gap-3">
                <button
                  onClick={handleRunSafetyCheck}
                  disabled={isAnalyzing}
                  className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-xl shadow-lg transition flex items-center gap-2 disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isAnalyzing ? "animate-spin" : ""}`} />
                  {isAnalyzing ? "Analyzing..." : "Re-evaluate Safety"}
                </button>
              </div>
            )}
          </div>

          {/* Patient Selector Bar */}
          <div className="bg-slate-900/70 border border-slate-800 p-4 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search patient by name or MRN..."
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs pl-9 pr-3 py-2 rounded-lg focus:outline-none focus:border-cyan-500"
                />
              </div>

              <select
                value={selectedPatient?.id || ""}
                onChange={(e) => {
                  const p = patients.find((pat) => pat.id === e.target.value);
                  if (p) setSelectedPatient(p);
                }}
                className="bg-slate-950 border border-slate-800 text-slate-200 text-xs px-3 py-2 rounded-lg focus:outline-none focus:border-cyan-500"
              >
                {filteredPatients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name} ({p.mrn})
                  </option>
                ))}
              </select>
            </div>

            {selectedPatient && (
              <div className="flex items-center gap-4 text-xs text-slate-400 self-stretch sm:self-auto justify-between sm:justify-end">
                <span>
                  Allergies:{" "}
                  <b className="text-amber-400 font-semibold">
                    {selectedPatient.known_allergies?.length > 0
                      ? selectedPatient.known_allergies.join(", ")
                      : "None Documented"}
                  </b>
                </span>
                <span>•</span>
                <span>
                  Active Prescriptions: <b className="text-cyan-300">{prescriptions.length}</b>
                </span>
              </div>
            )}
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-800 gap-2 text-xs font-bold">
            <button
              onClick={() => setActiveTab("prescriptions")}
              className={`pb-3 px-4 border-b-2 transition flex items-center gap-2 ${
                activeTab === "prescriptions"
                  ? "border-cyan-400 text-cyan-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Pill className="w-4 h-4" />
              Prescriptions & Medications ({prescriptions.length})
            </button>
            <button
              onClick={() => setActiveTab("safety")}
              className={`pb-3 px-4 border-b-2 transition flex items-center gap-2 ${
                activeTab === "safety"
                  ? "border-amber-400 text-amber-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              Safety Alerts ({safetyFindings.length})
            </button>
            <button
              onClick={() => setActiveTab("timeline")}
              className={`pb-3 px-4 border-b-2 transition flex items-center gap-2 ${
                activeTab === "timeline"
                  ? "border-emerald-400 text-emerald-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Clock className="w-4 h-4" />
              Longitudinal Timeline
            </button>
          </div>

          {/* Tab Content */}
          {isLoading ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center text-slate-400 space-y-3">
              <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
              <p className="text-sm font-semibold">Loading patient prescription records...</p>
            </div>
          ) : (
            <>
              {activeTab === "prescriptions" && (
                <div className="space-y-6">
                  {prescriptions.length === 0 ? (
                    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-10 text-center text-slate-400 space-y-2">
                      <Pill className="w-8 h-8 text-slate-600 mx-auto" />
                      <p className="text-sm font-bold text-slate-300">No prescription records found for this patient.</p>
                      <p className="text-xs text-slate-500">
                        Upload a digital or scanned prescription document via the Ingestion & Reports section.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Prescription Selector Buttons */}
                      {prescriptions.length > 1 && (
                        <div className="flex gap-2 overflow-x-auto pb-2">
                          {prescriptions.map((rx, i) => (
                            <button
                              key={rx.id}
                              onClick={() => setSelectedPrescription(rx)}
                              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap border transition ${
                                selectedPrescription?.id === rx.id
                                  ? "bg-cyan-950 text-cyan-300 border-cyan-500"
                                  : "bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800"
                              }`}
                            >
                              Prescription #{i + 1} ({rx.prescription_date?.slice(0, 10) || "Recent"})
                            </button>
                          ))}
                        </div>
                      )}

                      {selectedPrescription && (
                        <PrescriptionViewer
                          prescription={selectedPrescription}
                          onRunSafetyCheck={handleRunSafetyCheck}
                          isAnalyzing={isAnalyzing}
                          onSelectFinding={(f) => setReviewingFinding(f)}
                        />
                      )}
                    </div>
                  )}
                </div>
              )}

              {activeTab === "safety" && (
                <MedicationSafetyPanel
                  findings={safetyFindings}
                  onReviewFinding={(f) => setReviewingFinding(f)}
                />
              )}

              {activeTab === "timeline" && timeline && (
                <MedicationTimeline
                  timeline={timeline}
                  onSelectPrescription={(rxId) => {
                    const rx = prescriptions.find((p) => p.id === rxId);
                    if (rx) {
                      setSelectedPrescription(rx);
                      setActiveTab("prescriptions");
                    }
                  }}
                />
              )}
            </>
          )}

          {/* Clinician Review Modal */}
          {reviewingFinding && (
            <MedicationReviewModal
              finding={reviewingFinding}
              onClose={() => setReviewingFinding(null)}
              onSubmitReview={handleSubmitReview}
            />
          )}
        </main>
      </div>
    </div>
  );
}
