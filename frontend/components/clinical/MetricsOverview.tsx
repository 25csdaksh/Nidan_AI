import React from "react";
import { Activity, AlertOctagon, CheckCircle2, FileUp, HeartPulse, Users } from "lucide-react";

interface MetricsOverviewProps {
  totalPatients: number;
  totalReports: number;
  pendingJobs: number;
  abnormalitiesFlagged: number;
}

export function MetricsOverview({
  totalPatients,
  totalReports,
  pendingJobs,
  abnormalitiesFlagged,
}: MetricsOverviewProps) {
  const cards = [
    {
      label: "Registered Patients",
      value: totalPatients,
      icon: Users,
      color: "text-sky-400",
      bg: "bg-sky-500/10 border-sky-500/20",
      sub: "Active medical profiles",
    },
    {
      label: "Ingested Reports",
      value: totalReports,
      icon: FileUp,
      color: "text-teal-400",
      bg: "bg-teal-500/10 border-teal-500/20",
      sub: "Encrypted object store",
    },
    {
      label: "Lab Anomalies Monitored",
      value: abnormalitiesFlagged,
      icon: AlertOctagon,
      color: "text-amber-400",
      bg: "bg-amber-500/10 border-amber-500/20",
      sub: "Out-of-range reference limits",
    },
    {
      label: "CDSS Guardrail Status",
      value: "HITL Active",
      icon: CheckCircle2,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10 border-emerald-500/20",
      sub: "Zero autonomous diagnosis",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.label}
            className={`p-4 rounded-xl border ${card.bg} bg-slate-900/60 backdrop-blur transition hover:border-slate-700`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">{card.label}</span>
              <div className={`p-2 rounded-lg ${card.bg} ${card.color}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl font-bold tracking-tight text-white font-mono">
                {card.value}
              </span>
              <p className="text-[11px] text-slate-400 mt-0.5">{card.sub}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
