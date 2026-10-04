"use client";

import React from "react";
import Link from "next/link";
import { Activity, Bell, FileText, HeartPulse, Search, Shield, User } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-500 to-teal-400 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <HeartPulse className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold tracking-tight text-white text-base">NIDAN AI</span>
                <span className="text-[10px] bg-sky-950 text-sky-400 border border-sky-800 px-1.5 py-0.2 rounded font-mono">
                  v0.1.0-Phase0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5">Intelligent Clinical Insights</p>
            </div>
          </Link>
        </div>

        {/* Global Search */}
        <div className="hidden md:flex items-center flex-1 max-w-md mx-8">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by Patient MRN, Name, Lab Analyte, or ICD code..."
              className="w-full bg-slate-950/70 border border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
            />
          </div>
        </div>

        {/* Clinician Profile & Notifications */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-full px-2.5 py-1 text-xs text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-[11px] text-slate-400 font-mono">Broker: Ready</span>
          </div>

          <button className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-300 transition relative">
            <Bell className="w-4 h-4" />
            <span className="w-2 h-2 bg-sky-500 rounded-full absolute top-1.5 right-1.5"></span>
          </button>

          <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
            <div className="w-7 h-7 rounded-full bg-sky-900 border border-sky-700 flex items-center justify-center text-xs font-semibold text-sky-200">
              EV
            </div>
            <div className="hidden lg:block text-left">
              <p className="text-xs font-medium text-slate-200 leading-tight">Dr. Eleanor Vance</p>
              <p className="text-[10px] text-slate-400">Chief Attending Physician</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
