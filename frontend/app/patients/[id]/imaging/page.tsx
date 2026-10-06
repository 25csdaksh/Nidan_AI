"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  fetchPatientImagingStudies,
  fetchImagingStudyDetail,
  triggerImagingAnalysis,
  reviewImagingFinding,
  fetchImagingExplainability,
  fetchPatientImagingTimeline,
  getImagingImageUrl,
} from "@/lib/api";
import {
  ImagingStudy,
  ImagingStudyDetail,
  ImagingFinding,
  ImagingFindingReviewStatus,
  ImagingTimelineResponse,
} from "@/lib/types";
import { ImagingSafetyBanner } from "@/components/imaging/ImagingSafetyBanner";
import { XRayViewer } from "@/components/imaging/XRayViewer";
import { XRayUploadPanel } from "@/components/imaging/XRayUploadPanel";
import { ImagingStudyCard } from "@/components/imaging/ImagingStudyCard";
import { ImagingAnalysisPanel } from "@/components/imaging/ImagingAnalysisPanel";
import { ImagingReviewModal } from "@/components/imaging/ImagingReviewModal";
import { ImagingEvidenceDrawer } from "@/components/imaging/ImagingEvidenceDrawer";
import { ImagingTimeline } from "@/components/imaging/ImagingTimeline";

export default function PatientImagingPage() {
  const params = useParams();
  const patientId = params.id as string;

  const [activeTab, setActiveTab] = useState<"inspection" | "timeline" | "upload">("inspection");
  const [studies, setStudies] = useState<ImagingStudy[]>([]);
  const [selectedStudy, setSelectedStudy] = useState<ImagingStudyDetail | null>(null);
  const [timelineData, setTimelineData] = useState<ImagingTimelineResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overlays & Modals
  const [overlayHeatmap, setOverlayHeatmap] = useState<number[][] | undefined>(undefined);
  const [overlayBoxes, setOverlayBoxes] = useState<any[] | undefined>(undefined);
  const [activeFindingLabel, setActiveFindingLabel] = useState<string | undefined>(undefined);

  const [reviewingFinding, setReviewingFinding] = useState<ImagingFinding | null>(null);
  const [evidenceFinding, setEvidenceFinding] = useState<ImagingFinding | null>(null);

  const loadData = async (preferredStudyId?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const [studiesList, timeline] = await Promise.all([
        fetchPatientImagingStudies(patientId),
        fetchPatientImagingTimeline(patientId),
      ]);
      setStudies(studiesList);
      setTimelineData(timeline);

      const targetId = preferredStudyId || (studiesList.length > 0 ? studiesList[0].id : null);
      if (targetId) {
        const detail = await fetchImagingStudyDetail(targetId);
        setSelectedStudy(detail);
      } else {
        setSelectedStudy(null);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load patient imaging studies.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (patientId) {
      loadData();
    }
  }, [patientId]);

  const handleSelectStudy = async (studyId: string) => {
    setIsLoading(true);
    try {
      const detail = await fetchImagingStudyDetail(studyId);
      setSelectedStudy(detail);
      setOverlayHeatmap(undefined);
      setOverlayBoxes(undefined);
      setActiveFindingLabel(undefined);
      setActiveTab("inspection");
    } catch (err: any) {
      setError(err.message || "Failed to load study details.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleTriggerAnalysis = async () => {
    if (!selectedStudy) return;
    setIsLoading(true);
    try {
      await triggerImagingAnalysis(selectedStudy.id);
      await handleSelectStudy(selectedStudy.id);
    } catch (err: any) {
      setError(err.message || "Analysis failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewLocalization = async (finding: ImagingFinding) => {
    if (!selectedStudy || !selectedStudy.analyses.length) return;
    const latestAnalysis = selectedStudy.analyses[-1] || selectedStudy.analyses[0];
    try {
      const exp = await fetchImagingExplainability(latestAnalysis.id, finding.finding_code);
      setOverlayHeatmap(exp.heatmap_grid);
      setOverlayBoxes(exp.localization_boxes);
      setActiveFindingLabel(finding.finding_name);
    } catch (err: any) {
      // Fallback to finding's embedded bounding box if available
      if (finding.localization_json?.boxes) {
        setOverlayBoxes(finding.localization_json.boxes);
        setActiveFindingLabel(finding.finding_name);
      }
    }
  };

  const handleSubmitReview = async (
    findingId: string,
    status: ImagingFindingReviewStatus,
    comment: string,
    modifiedSeverity?: string
  ) => {
    await reviewImagingFinding(findingId, {
      review_status: status,
      clinician_comment: comment,
      modified_severity: modifiedSeverity,
    });
    if (selectedStudy) {
      await handleSelectStudy(selectedStudy.id);
    }
  };

  const activeImage = selectedStudy?.images?.[0];
  const imageUrl = activeImage ? getImagingImageUrl(activeImage.id) : null;
  const latestAnalysis = selectedStudy?.analyses?.[selectedStudy.analyses.length - 1];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <Link
              href="/patients"
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-slate-100 text-xs font-medium transition"
            >
              ← All Patients
            </Link>
            <span className="text-slate-600">/</span>
            <h1 className="text-lg md:text-xl font-bold text-slate-100 flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                </svg>
              </span>
              Medical Imaging Intelligence & Chest X-Ray
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("inspection")}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                activeTab === "inspection"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              Active Study
            </button>
            <button
              onClick={() => setActiveTab("timeline")}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                activeTab === "timeline"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              Imaging Timeline ({studies.length})
            </button>
            <button
              onClick={() => setActiveTab("upload")}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                activeTab === "upload"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              + Ingest X-Ray
            </button>
          </div>
        </div>

        {/* CDSS Safety Banner */}
        <ImagingSafetyBanner />

        {error && (
          <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
            {error}
          </div>
        )}

        {/* Tab 1: Upload Panel */}
        {activeTab === "upload" && (
          <div className="max-w-2xl mx-auto">
            <XRayUploadPanel
              patientId={patientId}
              onUploadSuccess={(newStudyId) => {
                loadData(newStudyId);
                setActiveTab("inspection");
              }}
            />
          </div>
        )}

        {/* Tab 2: Longitudinal Timeline */}
        {activeTab === "timeline" && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 className="text-base font-bold text-slate-100 mb-2">
              Longitudinal Chest Radiograph Trajectory
            </h2>
            <p className="text-xs text-slate-400 mb-6">
              Chronological review of patient chest radiographs, comparative probabilities, and clinician verification states.
            </p>
            <ImagingTimeline
              timeline={timelineData?.timeline || []}
              onSelectStudy={handleSelectStudy}
            />
          </div>
        )}

        {/* Tab 3: Active Inspection Workspace */}
        {activeTab === "inspection" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Sidebar: Studies List */}
            <div className="lg:col-span-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                  Patient Studies ({studies.length})
                </h3>
                <button
                  onClick={() => setActiveTab("upload")}
                  className="text-xs text-indigo-400 hover:underline"
                >
                  + Ingest
                </button>
              </div>

              {studies.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500 bg-slate-900/60 rounded-2xl border border-slate-800">
                  No imaging studies yet. Click &quot;+ Ingest X-Ray&quot; to upload.
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[720px] overflow-y-auto pr-1">
                  {studies.map((s) => (
                    <ImagingStudyCard
                      key={s.id}
                      study={s}
                      isSelected={selectedStudy?.id === s.id}
                      onSelect={(study) => handleSelectStudy(study.id)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Right Main Area: Interactive Viewer & Findings */}
            <div className="lg:col-span-8 space-y-6">
              {selectedStudy ? (
                <>
                  {/* PACS Interactive Viewer */}
                  {imageUrl ? (
                    <XRayViewer
                      imageUrl={imageUrl}
                      originalFilename={activeImage?.original_filename}
                      overlayHeatmap={overlayHeatmap}
                      overlayBoxes={overlayBoxes}
                      activeFindingLabel={activeFindingLabel}
                      onClearOverlay={() => {
                        setOverlayHeatmap(undefined);
                        setOverlayBoxes(undefined);
                        setActiveFindingLabel(undefined);
                      }}
                    />
                  ) : (
                    <div className="h-64 flex items-center justify-center bg-slate-900/80 rounded-2xl border border-slate-800 text-xs text-slate-500">
                      No image pixels attached to study record.
                    </div>
                  )}

                  {/* Analysis Run Controls & Findings */}
                  {latestAnalysis ? (
                    <ImagingAnalysisPanel
                      analysis={latestAnalysis}
                      onViewLocalization={handleViewLocalization}
                      onViewEvidence={(finding) => setEvidenceFinding(finding)}
                      onOpenReview={(finding) => setReviewingFinding(finding)}
                    />
                  ) : (
                    <div className="p-8 text-center bg-slate-900/80 rounded-2xl border border-slate-800 space-y-3">
                      <p className="text-xs text-slate-400">
                        Inference pipeline has not yet executed for this study.
                      </p>
                      <button
                        onClick={handleTriggerAnalysis}
                        disabled={isLoading}
                        className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition shadow-md"
                      >
                        {isLoading ? "Running Vision Pipeline..." : "Execute Vision Model Analysis"}
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <div className="h-[400px] flex flex-col items-center justify-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-500 space-y-3">
                  <p className="text-sm">Select an imaging study or ingest a new Chest X-Ray</p>
                  <button
                    onClick={() => setActiveTab("upload")}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-500"
                  >
                    + Upload Chest X-Ray
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Modals & Drawers */}
        {reviewingFinding && (
          <ImagingReviewModal
            finding={reviewingFinding}
            isOpen={!!reviewingFinding}
            onClose={() => setReviewingFinding(null)}
            onSubmitReview={handleSubmitReview}
          />
        )}

        {evidenceFinding && (
          <ImagingEvidenceDrawer
            finding={evidenceFinding}
            isOpen={!!evidenceFinding}
            onClose={() => setEvidenceFinding(null)}
          />
        )}
      </div>
    </div>
  );
}
