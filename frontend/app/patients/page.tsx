"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  Calendar,
  ChevronRight,
  Droplet,
  FileText,
  Heart,
  HeartPulse,
  Pill,
  Plus,
  Radio,
  Search,
  User,
  Users,
} from "lucide-react";
import { Patient } from "@/lib/types";
import { createPatient, fetchPatients } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    mrn: "",
    first_name: "",
    last_name: "",
    date_of_birth: "1990-01-01",
    gender: "female",
    blood_group: "O+",
    phone: "",
    email: "",
    known_allergies: "",
    chronic_conditions: "",
  });

  const loadPatients = async (query?: string) => {
    try {
      const data = await fetchPatients(query);
      setPatients(data);
      if (data.length > 0 && !selectedPatient) {
        setSelectedPatient(data[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadPatients(searchQuery);
  }, [searchQuery]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        known_allergies: formData.known_allergies
          ? formData.known_allergies.split(",").map((s) => s.trim())
          : [],
        chronic_conditions: formData.chronic_conditions
          ? formData.chronic_conditions.split(",").map((s) => s.trim())
          : [],
      };
      const created = await createPatient(payload);
      setIsModalOpen(false);
      await loadPatients();
      setSelectedPatient(created);
    } catch (err) {
      console.error("Failed creating patient", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Patient Longitudinal Registry</h1>
          <p className="text-xs text-slate-400">
            Unified medical history, demographic profile, and multi-visit clinical timeline.
          </p>
        </div>
        <button
          onClick={() => {
            setFormData({
              mrn: `MRN-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`,
              first_name: "",
              last_name: "",
              date_of_birth: "1990-01-01",
              gender: "female",
              blood_group: "A+",
              phone: "",
              email: "",
              known_allergies: "",
              chronic_conditions: "",
            });
            setIsModalOpen(true);
          }}
          className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1.5 self-start shadow-md shadow-sky-600/20"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Patient</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Patient Selector & Search */}
        <div className="space-y-4">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by MRN, name, phone..."
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>

          <div className="space-y-2 max-h-[calc(100vh-18rem)] overflow-y-auto pr-1">
            {patients.map((p) => {
              const isSelected = selectedPatient?.id === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => setSelectedPatient(p)}
                  className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                    isSelected
                      ? "bg-sky-950/40 border-sky-500/50 shadow-sm"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-xs font-semibold text-sky-400">
                      {p.first_name[0]}
                      {p.last_name[0]}
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-200">
                        {p.first_name} {p.last_name}
                      </p>
                      <p className="text-[10px] text-slate-500 font-mono">{p.mrn}</p>
                    </div>
                  </div>
                  <span className="text-[11px] text-slate-400 capitalize">{p.gender}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Selected Patient Dossier */}
        <div className="lg:col-span-2 space-y-5">
          {selectedPatient ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6">
              {/* Patient Banner */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
                <div className="flex items-center gap-3.5">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-base font-bold text-white shadow-lg shadow-sky-500/20">
                    {selectedPatient.first_name[0]}
                    {selectedPatient.last_name[0]}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-bold text-white">
                        {selectedPatient.first_name} {selectedPatient.last_name}
                      </h2>
                      <span className="text-xs bg-slate-800 font-mono text-sky-400 px-2 py-0.5 rounded border border-slate-700">
                        {selectedPatient.mrn}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      DOB: {formatDate(selectedPatient.date_of_birth)} ({selectedPatient.gender})
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  {selectedPatient.blood_group && (
                    <div className="px-2.5 py-1 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-300 font-medium flex items-center gap-1">
                      <Droplet className="w-3 h-3 text-rose-400" />
                      <span>Blood Group: {selectedPatient.blood_group}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Demographics & Clinical Profile */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2">
                  <h3 className="font-semibold text-slate-300 flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-sky-400" />
                    <span>Contact Information</span>
                  </h3>
                  <div className="space-y-1 text-slate-400 text-[11px]">
                    <p>Phone: {selectedPatient.phone || "Not recorded"}</p>
                    <p>Email: {selectedPatient.email || "Not recorded"}</p>
                    <p>Address: {selectedPatient.address || "Not recorded"}</p>
                  </div>
                </div>

                <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2">
                  <h3 className="font-semibold text-slate-300 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                    <span>Clinical Alerts & Allergies</span>
                  </h3>
                  <div className="space-y-1 text-[11px]">
                    <p className="text-slate-400">
                      Allergies:{" "}
                      {selectedPatient.known_allergies.length > 0 ? (
                        <span className="text-amber-400 font-medium">
                          {selectedPatient.known_allergies.join(", ")}
                        </span>
                      ) : (
                        "No known allergies"
                      )}
                    </p>
                    <p className="text-slate-400">
                      Chronic Conditions:{" "}
                      {selectedPatient.chronic_conditions.length > 0 ? (
                        <span className="text-slate-300">
                          {selectedPatient.chronic_conditions.join(", ")}
                        </span>
                      ) : (
                        "None recorded"
                      )}
                    </p>
                  </div>
                </div>
              </div>

              {/* Longitudinal Encounters & Modality History */}
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Diagnostic History & Ingested Modalities
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                  <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl">
                    <Activity className="w-4 h-4 text-sky-400 mx-auto mb-1" />
                    <span className="text-xs font-medium text-slate-200">Blood Tests</span>
                    <p className="text-[10px] text-slate-500">Panel Tracking</p>
                  </div>
                  <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl">
                    <Pill className="w-4 h-4 text-teal-400 mx-auto mb-1" />
                    <span className="text-xs font-medium text-slate-200">Prescriptions</span>
                    <p className="text-[10px] text-slate-500">Active Rx</p>
                  </div>
                  <Link
                    href={`/patients/${selectedPatient.id}/imaging`}
                    className="p-3 bg-slate-950/40 border border-slate-800 hover:border-indigo-500/80 rounded-xl transition block group"
                  >
                    <Radio className="w-4 h-4 text-indigo-400 mx-auto mb-1 group-hover:scale-110 transition-transform" />
                    <span className="text-xs font-medium text-slate-200 group-hover:text-indigo-300">X-Ray Intelligence</span>
                    <p className="text-[10px] text-slate-500">Chest Radiographs →</p>
                  </Link>
                  <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl">
                    <HeartPulse className="w-4 h-4 text-rose-400 mx-auto mb-1" />
                    <span className="text-xs font-medium text-slate-200">Sonography</span>
                    <p className="text-[10px] text-slate-500">Ultrasounds</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center text-slate-500 text-xs">
              Select a patient from the left column to inspect clinical profile.
            </div>
          )}
        </div>
      </div>

      {/* New Patient Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-semibold text-white">Create Patient Profile</h3>
            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 mb-1">MRN Number</label>
                  <input
                    type="text"
                    value={formData.mrn}
                    onChange={(e) => setFormData({ ...formData, mrn: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1">Blood Group</label>
                  <select
                    value={formData.blood_group}
                    onChange={(e) => setFormData({ ...formData, blood_group: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                  >
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 mb-1">First Name</label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1">Last Name</label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 mb-1">Date of Birth</label>
                  <input
                    type="date"
                    value={formData.date_of_birth}
                    onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1">Gender</label>
                  <select
                    value={formData.gender}
                    onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Known Allergies (comma separated)</label>
                <input
                  type="text"
                  placeholder="Penicillin, Sulfa, Peanuts"
                  value={formData.known_allergies}
                  onChange={(e) => setFormData({ ...formData, known_allergies: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-1.5 text-slate-400 hover:text-slate-200 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded font-medium transition"
                >
                  Save Patient
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
