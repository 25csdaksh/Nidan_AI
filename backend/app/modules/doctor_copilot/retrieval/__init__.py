"""
Evidence Retrieval & Relevance package for NIDAN AI Doctor Copilot.
"""
from app.modules.doctor_copilot.retrieval.relevance import classify_query, extract_query_entities
from app.modules.doctor_copilot.retrieval.evidence_retriever import EvidenceRetriever
from app.modules.doctor_copilot.retrieval.provenance import format_evidence_drilldown

__all__ = ["classify_query", "extract_query_entities", "EvidenceRetriever", "format_evidence_drilldown"]
