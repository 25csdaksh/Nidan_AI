"use client";

import React, { useState } from "react";
import { MedicationSafetyFinding, SafetySeverity } from "@/lib/types";
import {
  ShieldAlert,
  AlertTriangle,
  Info,
  CheckCircle2,
  FileText,
  Activity,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Filter,
} from "lucide-react";

interface MedicationSafetyPanelProps {
  findings: MedicationSafetyFinding[];
  onReviewFinding: (finding: MedicationSafetyFinding) => void;
}

export const MedicationSafetyPanel: React.FC<MedicationSafetyPanelProps> = ({
  findings,
  onReviewFinding,
}) => {
  const [selectedSeverity, setSelectedSeverity] = useState<string>("ALL");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [activeEvidenceFinding, setActiveEvidenceFinding] = useState<MedicationSafetyFinding | null>(null);

  const filteredFindings = findings.filter((f) => {
    const matchesSev = selectedSeverity === "ALL" || f.severity === selectedSeverity;
    const matchesType = selectedType === "ALL" || f.finding_type === selectedType;
    return matchesSev && matchesType;
  });

  const getSeverityBadge = (sev: SafetySeverity | string) => {
    switch (sev) {
      case "CRITICAL":
      case "HIGH":
        return <span className="px-2.5 py-1 bg-rose-950/80 text-rose-300 text-xs font-bold rounded-md border border-rose-700/50 flex items-center gap-1.5"><ShieldAlert className="w-3.5 h-3.5 text-rose-400" /> {sev}</span>;
      case "MODERATE":
        return <span className="px-2.5 py-1 bg-amber-950/80 text-amber-300 text-xs font-bold rounded-md border border-amber-700/50 flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> {sev}</span>;
      default:
        return <span className="px-2.5 py-1 bg-blue-950/80 text-blue-300 text-xs font-bold rounded-md border border-blue-700/50 flex items-center gap-1.5"><Info className="w-3.5 h-3.5 text-blue-400" /> {sev}</span>;
    }
  };

  const getFindingTypeIcon = (type: string) => {
    switch (type) {
      case "DRUG_DRUG_INTERACTION":
        return <Layers className="w-4 h-4 text-rose-400" />;
      case "POTENTIAL_ALLERGY_CONCERN":
        return <ShieldAlert className="w-4 h-4 text-amber-400" />;
      case "LAB_CONTEXT_SIGNAL":
        return <Activity className="w-4 h-4 text-cyan-400" />;
      case "POTENTIAL_DUPLICATE":
        return <Sparkles className="w-4 h-4 text-purple-400" />;
      default:
        return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-5 border-b border-slate-800">
        <div>
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            Medication Safety & Interaction Intelligence
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic CDSS Level 1/2 safety alerts based on documented prescriptions, allergies, and laboratory findings.
          </p>
        </div>

        <div className="flex items-center gap-2 self-stretch sm:self-auto text-xs">
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-slate-950 border border-slate-700 text-slate-200 px-3 py-1.5 rounded-lg focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Severities</option>
            <option value="HIGH">High / Critical</option>
            <option value="MODERATE">Moderate</option>
            <option value="INFO">Info / Low</option>
          </select>

          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-slate-950 border border-slate-700 text-slate-200 px-3 py-1.5 rounded-lg focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Alert Types</option>
            <option value="DRUG_DRUG_INTERACTION">Drug Interactions</option>
            <option value="POTENTIAL_ALLERGY_CONCERN">Allergy Concerns</option>
            <option value="LAB_CONTEXT_SIGNAL">Lab Context Signals</option>
            <option value="POTENTIAL_DUPLICATE">Duplicates</option>
            <option value="CONTRAINDICATION_SIGNAL">Contraindications</option>
          </select>
        </div>
      </div>

      {/* Findings Grid */}
      {filteredFindings.length === 0 ? (
        <div className="bg-slate-950/40 border border-slate-800/60 rounded-xl p-8 text-center text-slate-400 space-y-2">
          <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
          <p className="font-semibold text-slate-200 text-sm">No safety alerts matching the selected criteria.</p>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            All documented medications have been evaluated against active drug interaction, allergy, duplicate, and laboratory correlation rules.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredFindings.map((finding) => (
            <div
              key={finding.id}
              className="bg-slate-950/70 border border-slate-800 hover:border-slate-700 rounded-xl p-5 flex flex-col justify-between transition space-y-4 shadow-sm"
            >
              <div className="space-y-3">
                <div className="flex justify-between items-start gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-slate-900 border border-slate-800 rounded">
                      {getFindingTypeIcon(finding.finding_type)}
                    </div>
                    <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                      {finding.finding_type.replace(/_/g, " ")}
                    </span>
                  </div>
                  {getSeverityBadge(finding.severity)}
                </div>

                <div>
                  <h4 className="text-sm font-bold text-slate-100 leading-snug">{finding.title}</h4>
                  <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">{finding.description}</p>
                </div>

                {finding.clinical_association && (
                  <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-0.5">
                    <span className="text-slate-500 font-semibold block">Clinical Association</span>
                    <span className="text-slate-300">{finding.clinical_association}</span>
                  </div>
                )}
              </div>

              {/* Action Buttons & Evidence */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                <button
                  onClick={() => setActiveEvidenceFinding(finding)}
                  className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1 transition"
                >
                  <FileText className="w-3.5 h-3.5" />
                  View Provenance
                </button>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      finding.review_status === "ACCEPTED"
                        ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                        : finding.review_status === "MODIFIED"
                        ? "bg-blue-950 text-blue-300 border-blue-800"
                        : finding.review_status === "REJECTED"
                        ? "bg-rose-950 text-rose-300 border-rose-800"
                        : "bg-slate-800 text-amber-400 border-amber-800/40"
                    }`}
                  >
                    {finding.review_status}
                  </span>

                  <button
                    onClick={() => onReviewFinding(finding)}
                    className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition"
                  >
                    Review Alert
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Provenance Evidence Modal Drawer */}
      {activeEvidenceFinding && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in duration-150">
            <div className="flex justify-between items-center pb-3 border-b border-slate-800">
              <h4 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <FileText className="w-5 h-5 text-cyan-400" />
                Evidence Provenance & Verification
              </h4>
              <button
                onClick={() => setActiveEvidenceFinding(null)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">Finding Rule ID</span>
                  <span className="font-mono text-cyan-300 font-bold">{activeEvidenceFinding.rule_id || "DYNAMIC-001"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Rule Version</span>
                  <span className="font-mono text-slate-300">{activeEvidenceFinding.rule_version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Evidence Source</span>
                  <span className="text-slate-300 font-medium">
                    {activeEvidenceFinding.evidence?.source_reference || "Clinical Knowledge Catalog"}
                  </span>
                </div>
              </div>

              {activeEvidenceFinding.evidence?.source_text && (
                <div className="space-y-1">
                  <span className="text-slate-400 font-semibold block">Extracted Source Text:</span>
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-300 whitespace-pre-wrap">
                    {activeEvidenceFinding.evidence.source_text}
                  </div>
                </div>
              )}

              {activeEvidenceFinding.evidence?.lab_analyte && (
                <div className="bg-cyan-950/40 p-3 rounded-lg border border-cyan-800/60 space-y-1">
                  <span className="text-cyan-400 font-bold block flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5" /> Correlated Laboratory Finding
                  </span>
                  <p className="text-slate-200">
                    <span className="font-semibold">{activeEvidenceFinding.evidence.lab_analyte}</span>: {activeEvidenceFinding.evidence.lab_value} ({activeEvidenceFinding.evidence.lab_status})
                  </p>
                  {activeEvidenceFinding.evidence.lab_date && (
                    <span className="text-[10px] text-slate-400 block">Date: {activeEvidenceFinding.evidence.lab_date}</span>
                  )}
                </div>
              )}

              {activeEvidenceFinding.evidence?.allergy_match && (
                <div className="bg-amber-950/40 p-3 rounded-lg border border-amber-800/60 space-y-1">
                  <span className="text-amber-400 font-bold block flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5" /> Documented Allergy Correlation
                  </span>
                  <p className="text-slate-200">
                    Documented Allergy Class: <span className="font-semibold uppercase">{activeEvidenceFinding.evidence.allergy_match}</span>
                  </p>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setActiveEvidenceFinding(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition"
              >
                Close Provenance
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
