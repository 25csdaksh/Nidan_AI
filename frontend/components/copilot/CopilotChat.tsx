"use client";

import React, { useState, useRef, useEffect } from "react";
import { CopilotMessage as CopilotMessageType, EvidenceItem } from "@/lib/types";
import { CopilotMessage } from "./CopilotMessage";
import { CopilotQuickActions } from "./CopilotQuickActions";
import { CopilotSafetyBanner } from "./CopilotSafetyBanner";
import { Send, Loader2, Sparkles } from "lucide-react";

interface CopilotChatProps {
  messages: CopilotMessageType[];
  onSendMessage: (query: string) => Promise<void>;
  onSelectEvidence: (evidenceId: string) => void;
  evidenceItemsMap: Map<string, EvidenceItem>;
  loading: boolean;
}

export function CopilotChat({
  messages,
  onSendMessage,
  onSelectEvidence,
  evidenceItemsMap,
  loading,
}: CopilotChatProps) {
  const [inputQuery, setInputQuery] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || loading) return;
    const query = inputQuery.trim();
    setInputQuery("");
    await onSendMessage(query);
  };

  return (
    <div className="flex flex-col h-full bg-slate-950/60 rounded-xl border border-slate-800 overflow-hidden">
      {/* Top CDSS Safety Header */}
      <div className="p-3 border-b border-slate-800 bg-slate-900/60">
        <CopilotSafetyBanner />
      </div>

      {/* Message Thread */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="max-w-md space-y-1">
              <h4 className="text-base font-bold text-slate-100">
                NIDAN AI Doctor Copilot Ready
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Ask clinical trajectory questions, summarize laboratory encounters, check medication safety alerts, or review persistent abnormalities.
              </p>
            </div>
            <div className="w-full max-w-lg pt-2">
              <CopilotQuickActions
                onSelectAction={(q) => onSendMessage(q)}
                disabled={loading}
              />
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <CopilotMessage
              key={msg.id || idx}
              message={msg}
              onSelectEvidence={onSelectEvidence}
              evidenceItemsMap={evidenceItemsMap}
            />
          ))
        )}

        {loading && (
          <div className="flex gap-3 text-sm items-center text-slate-400 py-2">
            <div className="w-8 h-8 rounded-full bg-sky-500/20 flex items-center justify-center shrink-0">
              <Loader2 className="w-4 h-4 text-sky-400 animate-spin" />
            </div>
            <div className="text-xs font-medium text-sky-300">
              Synthesizing verified clinical evidence & running CDSS safety guardrails...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions (when conversation already started) */}
      {messages.length > 0 && (
        <div className="px-4 py-2 bg-slate-900/40 border-t border-slate-800/80">
          <CopilotQuickActions
            onSelectAction={(q) => onSendMessage(q)}
            disabled={loading}
          />
        </div>
      )}

      {/* Input Box */}
      <form
        onSubmit={handleSubmit}
        className="p-3 bg-slate-900 border-t border-slate-800 flex items-center gap-2"
      >
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="Ask a clinical question about this patient's verified records..."
          disabled={loading}
          className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!inputQuery.trim() || loading}
          className="px-4 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white rounded-lg text-sm font-semibold flex items-center gap-2 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          <span>Send</span>
        </button>
      </form>
    </div>
  );
}
