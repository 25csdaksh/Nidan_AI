from typing import Any, Dict, List, Set
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType, QueryType
from app.modules.doctor_copilot.retrieval.relevance import extract_query_entities


class EvidenceRetriever:
    """
    Ranks, filters, and bounds relevant evidence items based on query classification and entity focus.
    """

    def retrieve(
        self,
        query: str,
        query_type: QueryType,
        context: Dict[str, Any],
        max_evidence: int = 25,
    ) -> List[EvidenceItem]:
        all_evidence: List[EvidenceItem] = context.get("all_evidence", [])
        if not all_evidence:
            return []

        entities = extract_query_entities(query)
        scored_evidence: List[tuple[int, EvidenceItem]] = []

        for item in all_evidence:
            score = 0
            item_text = f"{item.title or ''} {item.value or ''} {item.source_text or ''} {str(item.details)}".lower()

            # 1. Entity Keyword Match (+50)
            if entities:
                for ent in entities:
                    if ent in item_text:
                        score += 50

            # 2. Query Type Alignment
            if query_type == QueryType.LAB_SUMMARY or query_type == QueryType.LAB_COMPARISON:
                if item.type in [EvidenceType.LAB_RESULT, EvidenceType.CLINICAL_FINDING]:
                    score += 30
            elif query_type == QueryType.TREND_QUERY:
                if item.type == EvidenceType.LONGITUDINAL_TREND:
                    score += 40
                elif item.type == EvidenceType.LAB_RESULT:
                    score += 20
            elif query_type == QueryType.ABNORMALITY_QUERY:
                if item.type == EvidenceType.CLINICAL_FINDING:
                    score += 40
                elif item.status in ["ABNORMAL", "CRITICAL_LOW", "CRITICAL_HIGH", "HIGH", "LOW"]:
                    score += 30
            elif query_type in [QueryType.MEDICATION_QUERY, QueryType.PRESCRIPTION_QUERY]:
                if item.type in [EvidenceType.MEDICATION, EvidenceType.PRESCRIPTION]:
                    score += 40
            elif query_type == QueryType.MEDICATION_SAFETY_QUERY:
                if item.type == EvidenceType.MEDICATION_SAFETY:
                    score += 50
                elif item.type in [EvidenceType.MEDICATION, EvidenceType.ALLERGY_RECORD, EvidenceType.LAB_RESULT]:
                    score += 20
            elif query_type in [QueryType.IMAGING_QUERY, QueryType.IMAGING_COMPARISON]:
                if item.type == EvidenceType.IMAGING_FINDING:
                    score += 60
                elif item.type in [EvidenceType.CLINICAL_FINDING, EvidenceType.DOCUMENT]:
                    score += 20
            elif query_type == QueryType.PATIENT_SUMMARY:
                # Balanced representation
                if item.type in [EvidenceType.CLINICAL_FINDING, EvidenceType.IMAGING_FINDING, EvidenceType.MEDICATION_SAFETY, EvidenceType.LONGITUDINAL_TREND]:
                    score += 25
                else:
                    score += 10

            # 3. Verified / Doctor-reviewed boost (+10)
            if item.review_status in ["VERIFIED", "ACCEPTED"]:
                score += 10

            scored_evidence.append((score, item))

        # Sort descending by score
        scored_evidence.sort(key=lambda x: x[0], reverse=True)

        # Select top non-zero or top max_evidence items
        selected: List[EvidenceItem] = []
        for score, item in scored_evidence:
            if len(selected) >= max_evidence:
                break
            selected.append(item)

        # If empty or all zero, fall back to first N items
        if not selected:
            selected = all_evidence[:max_evidence]

        return selected
