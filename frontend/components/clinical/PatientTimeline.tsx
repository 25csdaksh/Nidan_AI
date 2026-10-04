"use client";

import React, { useEffect, useState } from "react";
import {
  PatientTimelineResponse,
  TimelineVisitGroup,
  TimelineObservationItem,
  LongitudinalTrendItem,
  LongitudinalAnalysisResponse,
  LongitudinalSummarySection,
  LongitudinalReviewNote,
  CrossVisitComparisonResponse,
} from "@/lib/types";
import {
  getPatientTimeline,
  getPatientTrends,
  runLongitudinalAnalysis,
  getPatientLongitudinalAnalysis,
  comparePatientVisits,
  createLongitudinalReviewNote,
  listLongitudinalReviewNotes,
} from "@/lib/api";
import {
  Activity,
  Calendar,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  ArrowRight,
  GitCompare,
  FileText,
  ShieldAlert,
  Info,
  Layers,
  Sparkles,
  Search,
  Check,
  Clock,
  ChevronRight,
  ExternalLink,
  PlusCircle,
  HelpCircle,
  UserCheck,
} from "lucide-react";

interface PatientTimelineProps {
  patientId: string;
}

type ActiveTab = "timeline" | "summary" | "compare" | "notes";

export function PatientTimeline({ patientId }: PatientTimelineProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>("timeline");
  const [timeline, setTimeline] = useState<PatientTimelineResponse | null>(null);
  const [trends, setTrends] = useState<LongitudinalTrendItem[]>([]);
  const [analysis, setAnalysis] = useState<LongitudinalAnalysisResponse | null>(null);
  const [notes, setNotes] = useState<LongitudinalReviewNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected analyte for detail modal
  const [selectedTrend, setSelectedTrend] = useState<LongitudinalTrendItem | null>(null);

  // Comparison state
  const [visitA, setVisitA] = useState<string>("");
  const [visitB, setVisitB] = useState<string>("");
  const [comparisonResult, setComparisonResult] = useState<CrossVisitComparisonResponse | null>(null);
  const [comparing, setComparing] = useState(false);

  // Clinician note state
  const [newNote, setNewNote] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  // Provenance drawer state
  const [activeSectionProvenance, setActiveSectionProvenance] = useState<LongitudinalSummarySection | null>(null);

  // Initial load
  useEffect(() => {
    async function loadAllData() {
      if (!patientId) return;
      try {
        setLoading(true);
        setError(null);

        const [tLine, trList, anData, noteList] = await Promise.all([
          getPatientTimeline(patientId).catch(() => null),
          getPatientTrends(patientId).catch(() => []),
          getPatientLongitudinalAnalysis(patientId).catch(() => null),
          listLongitudinalReviewNotes(patientId).catch(() => []),
        ]);

        setTimeline(tLine);
        setTrends(trList || []);
        setAnalysis(anData);
        setNotes(noteList || []);

        // Default comparison visits if 2+ exist
        if (tLine && tLine.visits.length >= 2) {
          setVisitA(tLine.visits[0].document_id);
          setVisitB(tLine.visits[tLine.visits.length - 1].document_id);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load longitudinal clinical intelligence.");
      } finally {
        setLoading(false);
      }
    }
    loadAllData();
  }, [patientId]);

  // Handle visit comparison trigger
  const handleCompare = async () => {
    if (!visitA || !visitB || visitA === visitB) return;
    try {
      setComparing(true);
      const res = await comparePatientVisits(patientId, visitA, visitB);
      setComparisonResult(res);
    } catch (err: any) {
      alert(err.message || "Failed to compare visits");
    } finally {
      setComparing(false);
    }
  };

  // Handle new review note creation
  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    try {
      setSavingNote(true);
      const created = await createLongitudinalReviewNote(patientId, newNote, analysis?.id);
      setNotes([created, ...notes]);
      setNewNote("");
    } catch (err: any) {
      alert(err.message || "Failed to save clinician review note");
    } finally {
      setSavingNote(false);
    }
  };

  // Helper for trend badges
  const getTrendBadge = (trendStatus: string, direction: string, dynamics: string) => {
    if (dynamics === "PERSISTENT_ABNORMALITY") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
          <AlertOctagon className="w-3 h-3" />
          Persistent Abnormality
        </span>
      );
    }
    if (dynamics === "NEW_ABNORMALITY") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
          <AlertTriangle className="w-3 h-3" />
          New Finding
        </span>
      );
    }
    if (dynamics === "RESOLVED_ABNORMALITY" || trendStatus === "IMPROVING") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3" />
          Improving / Normalized
        </span>
      );
    }
    if (dynamics === "RECURRING_ABNORMALITY") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
          <Clock className="w-3 h-3" />
          Recurring Finding
        </span>
      );
    }
    if (dynamics === "FLUCTUATING" || trendStatus === "FLUCTUATING") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
          <Activity className="w-3 h-3" />
          Fluctuating
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
        <Minus className="w-3 h-3 text-slate-400" />
        Stable
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CRITICAL_LOW":
      case "CRITICAL_HIGH":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-600 text-white animate-pulse">CRITICAL</span>;
      case "LOW":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">LOW</span>;
      case "HIGH":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">HIGH</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">NORMAL</span>;
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 shadow-xl">
        <Activity className="w-10 h-10 animate-spin mx-auto text-indigo-400 mb-3" />
        <p className="text-sm font-semibold text-white">Synthesizing Patient Longitudinal Clinical Intelligence...</p>
        <p className="text-xs text-slate-400 mt-1">Cross-referencing verified encounters, trend trajectories, and pattern transitions</p>
      </div>
    );
  }

  if (error || !timeline || timeline.total_observations === 0) {
    return (
      <div className="bg-slate-950 border border-slate-800 rounded-2xl p-10 text-center text-slate-400 shadow-xl">
        <div className="w-12 h-12 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto mb-3 text-slate-500">
          <Calendar className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-slate-200">No Longitudinal Laboratory Encounters Found</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          Patient observations will automatically correlate into chronological timelines, trajectory engines, and visit comparisons as blood reports and lab documents are uploaded.
        </p>
      </div>
    );
  }

  const startDate = timeline.visits[0]?.visit_date || "Unknown";
  const endDate = timeline.visits[timeline.visits.length - 1]?.visit_date || "Unknown";

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col space-y-0">
      {/* -------------------------------------------------------------
          1. Header & Overview Banner
      ------------------------------------------------------------- */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 px-6 py-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase tracking-wider">
              CDSS Level 2
            </span>
            <h2 className="text-base font-bold text-white tracking-tight">PATIENT LONGITUDINAL INTELLIGENCE</h2>
          </div>
          <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-400">
            <span className="flex items-center gap-1.5 font-medium text-slate-300">
              <Calendar className="w-3.5 h-3.5 text-indigo-400" />
              Observation Period: <strong className="text-white">{startDate}</strong> → <strong className="text-white">{endDate}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              Reports Analyzed: <strong className="text-white">{timeline.total_visits}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-indigo-400" />
              Total Lab Observations: <strong className="text-white">{timeline.total_observations}</strong>
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center bg-slate-900/90 border border-slate-800 p-1 rounded-xl gap-1">
          <button
            onClick={() => setActiveTab("timeline")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === "timeline"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            Trends & Timeline
          </button>
          <button
            onClick={() => setActiveTab("summary")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === "summary"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Multi-Visit Summary
          </button>
          <button
            onClick={() => {
              setActiveTab("compare");
              if (!comparisonResult && visitA && visitB) handleCompare();
            }}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === "compare"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <GitCompare className="w-3.5 h-3.5" />
            Compare Visits
          </button>
          <button
            onClick={() => setActiveTab("notes")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === "notes"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Doctor Notes ({notes.length})
          </button>
        </div>
      </div>

      {/* Safety Boundary Notice */}
      <div className="bg-slate-900/60 border-b border-slate-800/80 px-6 py-2.5 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span>
            <strong>Clinical Decision Support Notice:</strong> Trends, transitions, and multi-visit summaries describe laboratory observation shifts. They do not constitute autonomous medical diagnoses or treatment prescriptions.
          </span>
        </div>
      </div>

      {/* -------------------------------------------------------------
          2. Tab Content Views
      ------------------------------------------------------------- */}
      <div className="p-6">
        {/* =========================================================
            TAB 1: TRENDS & CHRONOLOGICAL TIMELINE
        ========================================================= */}
        {activeTab === "timeline" && (
          <div className="space-y-8">
            {/* KEY TRENDS SECTION */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-400" />
                  Key Laboratory Trends & Trajectories
                </h3>
                <span className="text-[11px] text-slate-500">Click an analyte for full observation series</span>
              </div>

              {trends.length === 0 ? (
                <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-400 text-center">
                  At least 2 longitudinal report encounters required to calculate analyte trajectories.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {trends.map((t) => {
                    const points = t.history_points || [];
                    return (
                      <div
                        key={t.canonical_name}
                        onClick={() => setSelectedTrend(t)}
                        className="bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-xl p-4 cursor-pointer transition-all duration-200 shadow-sm hover:shadow-indigo-500/10 flex flex-col justify-between group"
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <h4 className="text-sm font-bold text-white group-hover:text-indigo-300 transition-colors">
                              {t.analyte}
                            </h4>
                            {t.direction === "INCREASED" && (
                              <div className="p-1 rounded bg-rose-500/10 text-rose-400">
                                <TrendingUp className="w-4 h-4" />
                              </div>
                            )}
                            {t.direction === "DECREASED" && (
                              <div className="p-1 rounded bg-blue-500/10 text-blue-400">
                                <TrendingDown className="w-4 h-4" />
                              </div>
                            )}
                            {t.direction === "UNCHANGED" && (
                              <div className="p-1 rounded bg-slate-800 text-slate-400">
                                <Minus className="w-4 h-4" />
                              </div>
                            )}
                          </div>

                          {/* Numerical Progression (e.g. 12.4 -> 11.1 -> 10.8 -> 10.2) */}
                          <div className="text-xs font-mono font-medium text-slate-300 flex flex-wrap items-center gap-1.5 my-2">
                            {points.map((pt, idx) => (
                              <React.Fragment key={idx}>
                                <span className={idx === points.length - 1 ? "text-white font-bold underline decoration-indigo-400" : "text-slate-400"}>
                                  {pt.value}
                                </span>
                                {idx < points.length - 1 && <span className="text-slate-600">→</span>}
                              </React.Fragment>
                            ))}
                            {t.unit && <span className="text-[10px] text-slate-500 font-sans">{t.unit}</span>}
                          </div>
                        </div>

                        <div className="pt-3 border-t border-slate-800/80 mt-2 flex items-center justify-between">
                          <div>{getTrendBadge(t.trend_status, t.direction, t.dynamics_classification)}</div>
                          <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-300 transition-colors" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* CHRONOLOGICAL ENCOUNTER TIMELINE */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-indigo-400" />
                  Chronological Encounter Timeline ({timeline.visits.length} Encounters)
                </h3>
              </div>

              <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
                {timeline.visits.map((visit, vIdx) => (
                  <div key={visit.document_id} className="relative group">
                    {/* Node Dot */}
                    <div className="absolute -left-6 top-1.5 w-4 h-4 rounded-full bg-slate-950 border-2 border-indigo-500 shadow-sm shadow-indigo-500/50 flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                    </div>

                    {/* Encounter Card */}
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all shadow-md">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800 mb-4">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-bold text-white">{visit.visit_date}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                            {visit.document_type.replace("_", " ")}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <span>Date Source: <strong>{visit.date_source}</strong></span>
                        </div>
                      </div>

                      {/* Observations Table */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                        {visit.observations.map((obs) => (
                          <div
                            key={obs.observation_id}
                            className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 flex flex-col justify-between"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <span className="text-xs font-semibold text-slate-200">{obs.analyte}</span>
                              {getStatusBadge(obs.status)}
                            </div>
                            <div className="mt-2 flex items-baseline justify-between">
                              <span className="text-base font-bold text-white font-mono">
                                {obs.value} <span className="text-[10px] text-slate-400 font-sans">{obs.unit}</span>
                              </span>
                              {obs.is_doctor_verified && (
                                <span className="text-[10px] text-emerald-400 flex items-center gap-0.5" title="Doctor Verified">
                                  <UserCheck className="w-3 h-3" /> Verified
                                </span>
                              )}
                            </div>
                            {(obs.reference_min !== null || obs.reference_max !== null) && (
                              <span className="text-[10px] text-slate-500 mt-1">
                                Ref: {obs.reference_min ?? "—"} – {obs.reference_max ?? "—"} {obs.unit}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* =========================================================
            TAB 2: MULTI-VISIT CLINICAL SUMMARY & PROVENANCE
        ========================================================= */}
        {activeTab === "summary" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  Deterministic Longitudinal Clinical Summary
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Multi-visit synthesis generated from structured verification rules with traceable provenance.
                </p>
              </div>
            </div>

            {(!analysis || analysis.sections.length === 0) ? (
              <div className="p-8 text-center text-slate-400 bg-slate-900 border border-slate-800 rounded-xl">
                No structured summary generated yet.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysis.sections.map((sec) => (
                  <div
                    key={sec.section_type}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition-colors shadow-sm"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 pb-2.5 border-b border-slate-800 mb-3">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                          {sec.title}
                        </h4>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {sec.safety_validation_status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-line font-sans">
                        {sec.generated_text}
                      </p>
                    </div>

                    {/* Why did NIDAN AI say this? Button */}
                    <div className="pt-3 border-t border-slate-800/80 mt-4 flex items-center justify-between">
                      <button
                        onClick={() => setActiveSectionProvenance(sec)}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium transition-colors"
                      >
                        <HelpCircle className="w-3.5 h-3.5" />
                        Why did NIDAN AI conclude this?
                      </button>
                      <span className="text-[10px] text-slate-500">v{sec.generation_version}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* =========================================================
            TAB 3: CROSS-VISIT COMPARISON MODE
        ========================================================= */}
        {activeTab === "compare" && (
          <div className="space-y-6">
            {/* Encounter Selectors */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
                <div className="w-full sm:w-auto">
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Baseline Encounter (Visit A):</label>
                  <select
                    value={visitA}
                    onChange={(e) => setVisitA(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-white rounded-lg px-3 py-2 text-xs font-medium focus:ring-1 focus:ring-indigo-500 focus:outline-none w-full"
                  >
                    {timeline.visits.map((v) => (
                      <option key={v.document_id} value={v.document_id}>
                        {v.visit_date} — {v.document_type.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="text-slate-600 hidden sm:block pt-5">
                  <ArrowRight className="w-5 h-5" />
                </div>

                <div className="w-full sm:w-auto">
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Comparison Encounter (Visit B):</label>
                  <select
                    value={visitB}
                    onChange={(e) => setVisitB(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-white rounded-lg px-3 py-2 text-xs font-medium focus:ring-1 focus:ring-indigo-500 focus:outline-none w-full"
                  >
                    {timeline.visits.map((v) => (
                      <option key={v.document_id} value={v.document_id}>
                        {v.visit_date} — {v.document_type.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                onClick={handleCompare}
                disabled={comparing || !visitA || !visitB || visitA === visitB}
                className="w-full md:w-auto px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-md shadow-indigo-600/30"
              >
                {comparing ? <Activity className="w-4 h-4 animate-spin" /> : <GitCompare className="w-4 h-4" />}
                Run Delta Comparison
              </button>
            </div>

            {/* Comparison Table */}
            {comparisonResult ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-md">
                <div className="px-5 py-3.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between text-xs font-semibold text-slate-300">
                  <span>Common Analytes Compared: {comparisonResult.common_analytes_count}</span>
                  <span>{comparisonResult.visit_a_date} vs {comparisonResult.visit_b_date}</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-900 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold">
                        <th className="py-3 px-4">Analyte</th>
                        <th className="py-3 px-4">Visit A ({comparisonResult.visit_a_date || "A"})</th>
                        <th className="py-3 px-4">Visit B ({comparisonResult.visit_b_date || "B"})</th>
                        <th className="py-3 px-4">Absolute Delta</th>
                        <th className="py-3 px-4">Status Transition</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {comparisonResult.items.map((item) => (
                        <tr key={item.canonical_name} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3 px-4 font-bold text-white">{item.analyte}</td>
                          <td className="py-3 px-4 font-mono text-slate-300">
                            {item.visit_a_value !== null ? `${item.visit_a_value} ${item.unit || ""}` : "—"}
                            <span className="ml-2">{getStatusBadge(item.visit_a_status || "")}</span>
                          </td>
                          <td className="py-3 px-4 font-mono text-slate-300">
                            {item.visit_b_value !== null ? `${item.visit_b_value} ${item.unit || ""}` : "—"}
                            <span className="ml-2">{getStatusBadge(item.visit_b_status || "")}</span>
                          </td>
                          <td className="py-3 px-4 font-mono">
                            {item.absolute_change !== null && item.absolute_change !== undefined ? (
                              <span className={`font-bold ${item.absolute_change > 0 ? "text-rose-400" : item.absolute_change < 0 ? "text-blue-400" : "text-slate-400"}`}>
                                {item.absolute_change > 0 ? `+${item.absolute_change}` : item.absolute_change} {item.unit || ""}
                                {item.percentage_change !== null && item.percentage_change !== undefined && (
                                  <span className="text-[10px] text-slate-500 ml-1">({item.percentage_change}%)</span>
                                )}
                              </span>
                            ) : "—"}
                          </td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-950 text-slate-300 border border-slate-800">
                              {item.status_transition}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-xs text-slate-500 bg-slate-900 border border-slate-800 rounded-xl">
                Select two encounters above and click "Run Delta Comparison" to see an analyte-by-analyte shift analysis.
              </div>
            )}
          </div>
        )}

        {/* =========================================================
            TAB 4: DOCTOR LONGITUDINAL REVIEW NOTES
        ========================================================= */}
        {activeTab === "notes" && (
          <div className="space-y-6">
            {/* Create Note Form */}
            <form onSubmit={handleAddNote} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <label className="text-xs font-bold text-white flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-indigo-400" />
                Append Clinician Longitudinal Review Note
              </label>
              <textarea
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="Document clinical observations, longitudinal correlation annotations, or follow-up notes..."
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-white placeholder-slate-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={savingNote || !newNote.trim()}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all disabled:opacity-50 flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
                >
                  {savingNote ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <PlusCircle className="w-3.5 h-3.5" />}
                  Save Clinician Note
                </button>
              </div>
            </form>

            {/* Note List */}
            <div className="space-y-3">
              {notes.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500 bg-slate-900 border border-slate-800 rounded-xl">
                  No clinician notes recorded for this patient's longitudinal record yet.
                </div>
              ) : (
                notes.map((note) => (
                  <div key={note.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-1.5">
                    <div className="flex items-center justify-between text-[11px] text-slate-400 pb-1.5 border-b border-slate-800">
                      <span className="font-semibold text-slate-300">Clinician Annotation</span>
                      <span>{note.created_at ? new Date(note.created_at).toLocaleString() : "Recently Added"}</span>
                    </div>
                    <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">{note.note}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* -------------------------------------------------------------
          3. Analyte Detail Modal
      ------------------------------------------------------------- */}
      {selectedTrend && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col">
            <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white">{selectedTrend.analyte} — Observation Series</h3>
                <p className="text-xs text-slate-400">Longitudinal trajectory across {selectedTrend.observation_count} encounters</p>
              </div>
              <button
                onClick={() => setSelectedTrend(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg text-xs font-semibold"
              >
                ✕ Close
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="flex items-center gap-3">
                {getTrendBadge(selectedTrend.trend_status, selectedTrend.direction, selectedTrend.dynamics_classification)}
                {selectedTrend.absolute_change !== null && selectedTrend.absolute_change !== undefined && (
                  <span className="text-xs font-mono text-slate-300">
                    Delta: {selectedTrend.absolute_change > 0 ? `+${selectedTrend.absolute_change}` : selectedTrend.absolute_change} {selectedTrend.unit} ({selectedTrend.percentage_change}%)
                  </span>
                )}
              </div>

              {/* History Table */}
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-950 text-slate-400 border-b border-slate-800 text-[11px] font-semibold uppercase">
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Observed Value</th>
                    <th className="py-2.5 px-3">Reference Range</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {(selectedTrend.history_points || []).map((pt, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30">
                      <td className="py-2.5 px-3 font-sans text-slate-300">{pt.date || "Unknown"}</td>
                      <td className="py-2.5 px-3 font-bold text-white">{pt.value} {pt.unit}</td>
                      <td className="py-2.5 px-3 text-slate-400 font-sans">{pt.reference_min ?? "—"} – {pt.reference_max ?? "—"} {pt.unit}</td>
                      <td className="py-2.5 px-3">{getStatusBadge(pt.status || "NORMAL")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* -------------------------------------------------------------
          4. Summary Section Provenance Modal ("Why did NIDAN AI say this?")
      ------------------------------------------------------------- */}
      {activeSectionProvenance && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl flex flex-col">
            <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-white">Summary Evidence Provenance</h3>
              </div>
              <button
                onClick={() => setActiveSectionProvenance(null)}
                className="text-slate-400 hover:text-white p-1 text-xs"
              >
                ✕
              </button>
            </div>
            <div className="p-6 space-y-4 text-xs text-slate-300">
              <div>
                <strong className="text-white block mb-1">Section:</strong>
                <span className="text-indigo-300 font-semibold">{activeSectionProvenance.title}</span>
              </div>
              <div>
                <strong className="text-white block mb-1">Generated Text:</strong>
                <p className="bg-slate-950 p-3 rounded-lg border border-slate-800 whitespace-pre-line text-slate-300">
                  {activeSectionProvenance.generated_text}
                </p>
              </div>
              <div>
                <strong className="text-white block mb-1">Underlying Evidence IDs:</strong>
                <div className="flex flex-wrap gap-1 font-mono text-[10px]">
                  {activeSectionProvenance.evidence_ids.map((id) => (
                    <span key={id} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {id.slice(0, 8)}...
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <strong className="text-white block mb-1">Rule Engine Version:</strong>
                <span className="text-slate-400">v{activeSectionProvenance.generation_version} (Deterministic CDSS)</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
