"use client";

import React, { useState, useEffect } from "react";
import { Patient } from "@/lib/types";
import { fetchPatients } from "@/lib/api";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { Bot, Users, Search, Sparkles, ShieldAlert, Loader2 } from "lucide-react";

export default function CopilotPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      setLoading(true);
      const data = await fetchPatients();
      setPatients(data);
      if (data.length > 0 && !selectedPatient) {
        setSelectedPatient(data[0]);
      }
    } catch (e) {
      console.error("Failed to load patients:", e);
    } finally {
      setLoading(false);
    }
  };

  const filteredPatients = patients.filter(
    (p) =>
      `${p.first_name} ${p.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.mrn.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-sky-500/20">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-100 tracking-tight flex items-center gap-2.5">
              Doctor AI Copilot
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
                Phase 6 CDSS
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Evidence-grounded clinical decision-support assistant with deterministic citations and HIPAA-compliant patient isolation.
            </p>
          </div>
        </div>

        {/* Patient Selection Bar */}
        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search patient MRN or name..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
            />
          </div>

          <select
            value={selectedPatient?.id || ""}
            onChange={(e) => {
              const found = patients.find((p) => p.id === e.target.value);
              if (found) setSelectedPatient(found);
            }}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 focus:outline-none focus:border-sky-500"
          >
            {filteredPatients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.first_name} {p.last_name} ({p.mrn})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Copilot Workspace */}
      {loading ? (
        <div className="h-[600px] flex items-center justify-center bg-slate-900/50 rounded-2xl border border-slate-800 text-slate-400 gap-2 text-sm">
          <Loader2 className="w-5 h-5 animate-spin text-sky-400" />
          <span>Loading patient clinical records & context catalog...</span>
        </div>
      ) : selectedPatient ? (
        <CopilotPanel patient={selectedPatient} />
      ) : (
        <div className="h-[500px] flex flex-col items-center justify-center bg-slate-900/50 rounded-2xl border border-slate-800 text-slate-400 text-center p-6 space-y-3">
          <Users className="w-10 h-10 text-slate-600" />
          <h3 className="text-base font-bold text-slate-200">No Patient Selected</h3>
          <p className="text-xs text-slate-400 max-w-sm">
            Please register or select a patient from your clinical roster to start evidence-grounded Copilot consultations.
          </p>
        </div>
      )}
    </div>
  );
}
