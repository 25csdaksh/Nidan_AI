"use client";

import React from "react";
import { Sparkles, Activity, FileCheck, AlertTriangle, Pill, Clock, HelpCircle } from "lucide-react";

interface CopilotQuickActionsProps {
  onSelectAction: (query: string) => void;
  disabled?: boolean;
}

const QUICK_ACTIONS = [
  {
    label: "Summarize Patient",
    query: "Summarize this patient's clinical status and laboratory trajectory before consultation.",
    icon: Sparkles,
    color: "text-purple-400 border-purple-500/20 bg-purple-500/10 hover:bg-purple-500/20",
  },
  {
    label: "Recent Lab Anomalies",
    query: "Show all abnormal laboratory values and critical findings currently present.",
    icon: AlertTriangle,
    color: "text-amber-400 border-amber-500/20 bg-amber-500/10 hover:bg-amber-500/20",
  },
  {
    label: "Compare Latest Reports",
    query: "Compare the latest two laboratory encounters and show what changed.",
    icon: Activity,
    color: "text-sky-400 border-sky-500/20 bg-sky-500/10 hover:bg-sky-500/20",
  },
  {
    label: "Medication Safety",
    query: "Are there medication safety findings, drug interactions, or allergy concerns that require review?",
    icon: Pill,
    color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/10 hover:bg-emerald-500/20",
  },
  {
    label: "Longitudinal Trends",
    query: "What longitudinal trajectories and persistent abnormalities are documented?",
    icon: Clock,
    color: "text-blue-400 border-blue-500/20 bg-blue-500/10 hover:bg-blue-500/20",
  },
  {
    label: "Data Quality & Gaps",
    query: "What information or laboratory panels are missing from the available records?",
    icon: HelpCircle,
    color: "text-indigo-400 border-indigo-500/20 bg-indigo-500/10 hover:bg-indigo-500/20",
  },
];

export function CopilotQuickActions({ onSelectAction, disabled }: CopilotQuickActionsProps) {
  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
        Clinical Quick Prompts
      </div>
      <div className="flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((action, idx) => {
          const Icon = action.icon;
          return (
            <button
              key={idx}
              type="button"
              disabled={disabled}
              onClick={() => onSelectAction(action.query)}
              className={`text-xs font-medium px-3 py-1.5 rounded-lg border transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed ${action.color}`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{action.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
