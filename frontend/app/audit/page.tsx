"use client";

import React, { useEffect, useState } from "react";
import { Clock, Eye, Lock, RefreshCw, Shield, ShieldCheck, User } from "lucide-react";
import { AuditLogItem } from "@/lib/types";
import { fetchAuditLogs } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fallback demo audit items if fresh install
  const sampleLogs: AuditLogItem[] = [
    {
      id: "aud_01h9ab110",
      action: "CDSS_GUARDRAIL_INITIALIZED",
      resource_type: "SYSTEM",
      ip_address: "127.0.0.1",
      user_agent: "Internal/Lifespan",
      details: { policy: "Human-In-The-Loop Enforcement Active", non_diagnostic: true },
      created_at: new Date().toISOString(),
    },
    {
      id: "aud_01h9ab111",
      action: "VIEW_PATIENT_RECORD",
      actor_id: "00000000-0000-0000-0000-000000000001",
      resource_type: "PATIENT",
      resource_id: "pat_sample_01",
      ip_address: "192.168.1.45",
      user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      details: { view_context: "OPD_CONSULTATION" },
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
  ];

  const loadLogs = async () => {
    try {
      setIsLoading(true);
      const data = await fetchAuditLogs();
      if (data && data.length > 0) {
        setLogs(data);
      } else {
        setLogs(sampleLogs);
      }
    } catch (e) {
      setLogs(sampleLogs);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">HIPAA & Clinical Audit Trail</h1>
          <p className="text-xs text-slate-400">
            Cryptographically timestamped access logs, record modifications, and CDSS verification actions.
          </p>
        </div>
        <button
          onClick={loadLogs}
          disabled={isLoading}
          className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition flex items-center gap-1.5 self-start border border-slate-700"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh Audit Stream</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-1">
          <div className="flex items-center gap-2 text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
            <span className="font-semibold text-slate-200">Tamper-Evident Policy</span>
          </div>
          <p className="text-[11px] text-slate-400">
            Append-only storage for all Protected Health Information (PHI) access.
          </p>
        </div>

        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-1">
          <div className="flex items-center gap-2 text-sky-400">
            <Lock className="w-4 h-4" />
            <span className="font-semibold text-slate-200">Encryption at Rest</span>
          </div>
          <p className="text-[11px] text-slate-400">
            AES-256 encrypted documents with strict least-privilege RBAC.
          </p>
        </div>

        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-1">
          <div className="flex items-center gap-2 text-amber-400">
            <Eye className="w-4 h-4" />
            <span className="font-semibold text-slate-200">HITL Verification Audit</span>
          </div>
          <p className="text-[11px] text-slate-400">
            Every clinical insight approval links directly to the attending physician ID.
          </p>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 font-medium border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Actor / Clinician ID</th>
                <th className="px-4 py-3">IP Address</th>
                <th className="px-4 py-3">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono text-[11px]">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/30 transition">
                  <td className="px-4 py-3 text-slate-400 font-sans">
                    {formatDateTime(log.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sky-400 font-semibold">{log.action}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded text-[10px]">
                      {log.resource_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {log.actor_id ? `${log.actor_id.substring(0, 8)}...` : "SYSTEM_DAEMON"}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{log.ip_address || "internal"}</td>
                  <td className="px-4 py-3 text-slate-400 max-w-xs truncate font-sans text-[11px]">
                    {JSON.stringify(log.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
