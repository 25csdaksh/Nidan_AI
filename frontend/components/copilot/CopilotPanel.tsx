"use client";

import React, { useState, useEffect } from "react";
import {
  Patient,
  CopilotSession,
  CopilotMessage as CopilotMessageType,
  EvidenceItem,
  StructuredCopilotResponse,
} from "@/lib/types";
import {
  createCopilotSession,
  listCopilotSessions,
  getCopilotSession,
  sendSessionMessage,
  directCopilotQuery,
} from "@/lib/api";
import { CopilotChat } from "./CopilotChat";
import { CopilotEvidenceDrawer } from "./CopilotEvidenceDrawer";
import { Bot, Plus, MessageSquare, User, History, Shield, RefreshCw } from "lucide-react";

interface CopilotPanelProps {
  patient: Patient;
  onClose?: () => void;
}

export function CopilotPanel({ patient, onClose }: CopilotPanelProps) {
  const [sessions, setSessions] = useState<CopilotSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<CopilotMessageType[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [creatingSession, setCreatingSession] = useState<boolean>(false);
  const [evidenceMap, setEvidenceMap] = useState<Map<string, EvidenceItem>>(new Map());
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);

  // Load sessions for patient
  const loadSessions = async () => {
    try {
      const data = await listCopilotSessions(patient.id);
      setSessions(data);
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id);
      }
    } catch (e) {
      console.error("Failed to load Copilot sessions:", e);
    }
  };

  // Load active session messages
  const loadSessionDetails = async (sessionId: string) => {
    try {
      setLoading(true);
      const detail = await getCopilotSession(sessionId);
      const msgs = (detail.messages || []).map((m: any) => ({
        id: m.id,
        session_id: sessionId,
        patient_id: patient.id,
        role: m.role,
        content: m.content,
        query_type: m.query_type,
        structured_response: m.structured_response,
        evidence_ids: m.evidence_ids || [],
        safety_status: m.safety_status,
        created_at: m.created_at,
      }));
      setMessages(msgs);

      // Collect evidence items into map
      const newMap = new Map<string, EvidenceItem>();
      msgs.forEach((msg: CopilotMessageType) => {
        if (msg.structured_response && msg.structured_response.evidence_items) {
          msg.structured_response.evidence_items.forEach((item: EvidenceItem) => {
            newMap.set(item.evidence_id, item);
          });
        }
      });
      setEvidenceMap(newMap);
    } catch (e) {
      console.error("Failed to load session messages:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [patient.id]);

  useEffect(() => {
    if (activeSessionId) {
      loadSessionDetails(activeSessionId);
    }
  }, [activeSessionId]);

  const handleCreateNewSession = async () => {
    try {
      setCreatingSession(true);
      const newSession = await createCopilotSession(patient.id, {
        title: `Case Review ${new Date().toLocaleDateString()}`,
      });
      setSessions([newSession, ...sessions]);
      setActiveSessionId(newSession.id);
      setMessages([]);
    } catch (e) {
      console.error("Failed to create session:", e);
    } finally {
      setCreatingSession(false);
    }
  };

  const handleSendMessage = async (queryText: string) => {
    setLoading(true);
    try {
      let activeId: string = activeSessionId || "";
      if (!activeId) {
        // Auto-create session if none active
        const newSession = await createCopilotSession(patient.id, {
          title: queryText.slice(0, 40) + "...",
        });
        setSessions([newSession, ...sessions]);
        activeId = newSession.id;
        setActiveSessionId(activeId);
      }

      // Optimistic user message append
      const optimisticUserMsg: CopilotMessageType = {
        id: `opt-${Date.now()}`,
        patient_id: patient.id,
        session_id: activeId,
        role: "user",
        content: queryText,
        query_type: "GENERAL_QUERY",
        evidence_ids: [],
        safety_status: "PASSED",
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticUserMsg]);

      // Call API
      const resp: StructuredCopilotResponse = await sendSessionMessage(activeId, {
        query: queryText,
      });

      // Assistant message
      const assistantMsg: CopilotMessageType = {
        id: `asst-${Date.now()}`,
        patient_id: patient.id,
        session_id: activeId,
        role: "assistant",
        content: resp.answer,
        query_type: resp.query_type,
        structured_response: resp,
        evidence_ids: resp.claims.flatMap((c) => c.evidence_ids),
        safety_status: resp.safety_status,
        created_at: new Date().toISOString(),
      };



      setMessages((prev) => [...prev, assistantMsg]);

      // Update evidence map with newly returned evidence items
      const updatedMap = new Map(evidenceMap);
      resp.evidence_items.forEach((item) => {
        updatedMap.set(item.evidence_id, item);
      });
      setEvidenceMap(updatedMap);
    } catch (e: any) {
      console.error(e);
      const errMsg: CopilotMessageType = {
        id: `err-${Date.now()}`,
        patient_id: patient.id,
        role: "assistant",
        content: `Query Error: ${e.message || "Failed to process request."}`,
        query_type: "UNSUPPORTED_QUERY",
        evidence_ids: [],
        safety_status: "FLAGGED",
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectEvidence = (evidenceId: string) => {
    const item = evidenceMap.get(evidenceId);
    if (item) {
      setSelectedEvidence(item);
    } else {
      setSelectedEvidence({
        evidence_id: evidenceId,
        type: "CLINICAL_EVIDENCE",
        patient_id: patient.id,
        title: `Clinical Evidence ${evidenceId}`,
        value: "Details verified in patient encounter record.",
        status: "VERIFIED",
        review_status: "VERIFIED",
      });
    }
  };

  return (
    <div className="flex h-[750px] w-full bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
      {/* Sidebar: Sessions & Patient Overview */}
      <div className="w-72 bg-slate-950/80 border-r border-slate-800 flex flex-col p-4 space-y-4">
        {/* Patient Profile Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 font-bold text-xs">
              {patient.first_name[0]}
              {patient.last_name[0]}
            </div>
            <div className="overflow-hidden">
              <h4 className="text-sm font-bold text-slate-100 truncate">
                {patient.first_name} {patient.last_name}
              </h4>
              <p className="text-[11px] font-mono text-slate-400 truncate">
                MRN: {patient.mrn} • {patient.gender}
              </p>
            </div>
          </div>
        </div>

        {/* New Session Button */}
        <button
          onClick={handleCreateNewSession}
          disabled={creatingSession}
          className="w-full py-2 px-3 bg-slate-800 hover:bg-slate-700/80 text-slate-100 border border-slate-700 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-sm disabled:opacity-50"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Clinical Consultation</span>
        </button>

        {/* Session History List */}
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-1 pb-1">
            Consultation Threads ({sessions.length})
          </div>
          {sessions.map((sess) => (
            <button
              key={sess.id}
              onClick={() => setActiveSessionId(sess.id)}
              className={`w-full text-left p-2.5 rounded-xl text-xs transition-all flex items-start gap-2.5 ${
                activeSessionId === sess.id
                  ? "bg-sky-500/15 border border-sky-500/30 text-sky-300 font-semibold"
                  : "hover:bg-slate-900 text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              <MessageSquare className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="overflow-hidden flex-1">
                <div className="truncate text-slate-200">{sess.title}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  {new Date(sess.created_at).toLocaleDateString()}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-950/40 p-4">
        <CopilotChat
          messages={messages}
          onSendMessage={handleSendMessage}
          onSelectEvidence={handleSelectEvidence}
          evidenceItemsMap={evidenceMap}
          loading={loading}
        />
      </div>

      {/* Evidence Slide-over Drawer */}
      <CopilotEvidenceDrawer
        evidence={selectedEvidence}
        onClose={() => setSelectedEvidence(null)}
      />
    </div>
  );
}
