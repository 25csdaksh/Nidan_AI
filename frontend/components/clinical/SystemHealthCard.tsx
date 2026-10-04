import React from "react";
import { CheckCircle2, Database, HardDrive, Layers, Server } from "lucide-react";
import { SystemHealth } from "@/lib/types";

interface SystemHealthCardProps {
  health: SystemHealth | null;
}

export function SystemHealthCard({ health }: SystemHealthCardProps) {
  if (!health) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 animate-pulse">
        <div className="h-4 bg-slate-800 rounded w-1/3 mb-2"></div>
        <div className="h-3 bg-slate-800 rounded w-2/3"></div>
      </div>
    );
  }

  const isHealthy = health.status === "healthy";

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-semibold text-slate-200">System Infrastructure</span>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
            isHealthy
              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
              : "bg-amber-950 text-amber-400 border border-amber-800"
          }`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
          {health.status.toUpperCase()}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-800/60 text-xs">
        <div className="p-2 bg-slate-950/60 rounded-lg border border-slate-800/80">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
            <Database className="w-3 h-3 text-sky-400" />
            <span>Database</span>
          </div>
          <p className="font-mono text-[11px] text-slate-200 mt-1 capitalize font-medium">
            {health.components.database}
          </p>
        </div>

        <div className="p-2 bg-slate-950/60 rounded-lg border border-slate-800/80">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
            <Layers className="w-3 h-3 text-teal-400" />
            <span>Task Broker</span>
          </div>
          <p className="font-mono text-[11px] text-slate-200 mt-1 capitalize font-medium">
            {health.components.broker}
          </p>
        </div>

        <div className="p-2 bg-slate-950/60 rounded-lg border border-slate-800/80">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
            <HardDrive className="w-3 h-3 text-amber-400" />
            <span>Storage</span>
          </div>
          <p className="font-mono text-[11px] text-slate-200 mt-1 capitalize font-medium">
            {health.components.storage.backend}
          </p>
        </div>
      </div>
    </div>
  );
}
