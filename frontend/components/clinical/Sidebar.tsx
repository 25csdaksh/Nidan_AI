"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Cpu,
  FileSpreadsheet,
  FileText,
  FolderOpen,
  HeartPulse,
  History,
  LayoutDashboard,
  Pill,
  Radio,
  Settings,
  Shield,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigationItems = [
  { name: "Clinical Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Patients Directory", href: "/patients", icon: Users },
  { name: "Ingestion & Reports", href: "/reports", icon: FolderOpen },
  { name: "Audit Trail (HIPAA)", href: "/audit", icon: Shield },
];

const modalityCategories = [
  { name: "Blood Reports", icon: Activity, count: "Active" },
  { name: "Prescriptions (Rx)", icon: Pill, count: "Active" },
  { name: "X-Rays & Radiographs", icon: Radio, count: "Active" },
  { name: "Sonography / USG", icon: HeartPulse, count: "Active" },
  { name: "General Lab Panels", icon: FileSpreadsheet, count: "Active" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0 min-h-[calc(100vh-6rem)]">
      <div className="p-4 space-y-6">
        <div>
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider px-3 mb-2">
            Navigation
          </p>
          <nav className="space-y-1">
            {navigationItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition",
                    isActive
                      ? "bg-sky-500/10 text-sky-400 border border-sky-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                  )}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div>
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider px-3 mb-2">
            Supported Modalities
          </p>
          <div className="space-y-1">
            {modalityCategories.map((cat) => {
              const Icon = cat.icon;
              return (
                <div
                  key={cat.name}
                  className="flex items-center justify-between px-3 py-1.5 rounded-lg text-xs text-slate-300 hover:bg-slate-800/40 transition"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-[11px]">{cat.name}</span>
                  </div>
                  <span className="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-mono">
                    {cat.count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2 text-sky-400 text-xs font-medium">
            <Cpu className="w-3.5 h-3.5" />
            <span>Phase 0 Pipeline</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Data models, schemas, and object storage are active. AI model extraction is reserved for Phase 1.
          </p>
        </div>
      </div>

      <div className="p-4 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
        <span>NIDAN Core CDSS</span>
        <span className="font-mono text-emerald-400">Ready</span>
      </div>
    </aside>
  );
}
