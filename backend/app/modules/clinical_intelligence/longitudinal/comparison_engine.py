from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.modules.clinical_intelligence.models import ClinicalObservation


class VisitComparisonItem(BaseModel):
    analyte: str
    canonical_name: str
    unit: Optional[str] = None
    visit_a_value: Optional[float] = None
    visit_a_raw_value: Optional[str] = None
    visit_a_status: Optional[str] = None
    visit_b_value: Optional[float] = None
    visit_b_raw_value: Optional[str] = None
    visit_b_status: Optional[str] = None
    absolute_change: Optional[float] = None
    percentage_change: Optional[float] = None
    status_transition: str  # e.g. "NORMAL -> LOW", "LOW -> NORMAL", "UNCHANGED"
    direction: str  # INCREASED, DECREASED, UNCHANGED, NOT_COMPARABLE


class CrossVisitComparisonResult(BaseModel):
    patient_id: str
    visit_a_document_id: str
    visit_a_date: Optional[str] = None
    visit_b_document_id: str
    visit_b_date: Optional[str] = None
    common_analytes_count: int
    items: List[VisitComparisonItem] = Field(default_factory=list)


class CrossVisitComparisonEngine:
    @classmethod
    def compare_visits(
        cls,
        patient_id: str,
        visit_a_doc_id: str,
        visit_a_obs: List[ClinicalObservation],
        visit_b_doc_id: str,
        visit_b_obs: List[ClinicalObservation],
    ) -> CrossVisitComparisonResult:
        a_map: Dict[str, ClinicalObservation] = {
            (o.canonical_name or o.analyte).strip().lower(): o for o in visit_a_obs
        }
        b_map: Dict[str, ClinicalObservation] = {
            (o.canonical_name or o.analyte).strip().lower(): o for o in visit_b_obs
        }

        all_keys = list(dict.fromkeys(list(a_map.keys()) + list(b_map.keys())))
        comparison_items: List[VisitComparisonItem] = []

        visit_a_date = visit_a_obs[0].observation_date.strftime("%Y-%m-%d") if visit_a_obs and visit_a_obs[0].observation_date else None
        visit_b_date = visit_b_obs[0].observation_date.strftime("%Y-%m-%d") if visit_b_obs and visit_b_obs[0].observation_date else None

        for k in all_keys:
            oa = a_map.get(k)
            ob = b_map.get(k)

            analyte_name = (ob.analyte if ob else None) or (oa.analyte if oa else k.title())
            cname = (ob.canonical_name if ob else None) or (oa.canonical_name if oa else k.title())
            unit = (ob.unit if ob else None) or (oa.unit if oa else None)

            va = oa.normalized_value if oa else None
            vb = ob.normalized_value if ob else None
            sa = oa.technical_status if oa else "UNMEASURED"
            sb = ob.technical_status if ob else "UNMEASURED"

            abs_change = None
            pct_change = None
            direction = "NOT_COMPARABLE"
            status_trans = f"{sa} -> {sb}"

            if va is not None and vb is not None:
                abs_change = round(vb - va, 3)
                if va != 0:
                    pct_change = round(((vb - va) / abs(va)) * 100.0, 2)

                if abs_change > 0:
                    direction = "INCREASED"
                elif abs_change < 0:
                    direction = "DECREASED"
                else:
                    direction = "UNCHANGED"

            comparison_items.append(
                VisitComparisonItem(
                    analyte=analyte_name,
                    canonical_name=cname,
                    unit=unit,
                    visit_a_value=va,
                    visit_a_raw_value=oa.value if oa else None,
                    visit_a_status=sa,
                    visit_b_value=vb,
                    visit_b_raw_value=ob.value if ob else None,
                    visit_b_status=sb,
                    absolute_change=abs_change,
                    percentage_change=pct_change,
                    status_transition=status_trans,
                    direction=direction,
                )
            )

        common_cnt = len([item for item in comparison_items if item.visit_a_value is not None and item.visit_b_value is not None])

        return CrossVisitComparisonResult(
            patient_id=patient_id,
            visit_a_document_id=visit_a_doc_id,
            visit_a_date=visit_a_date,
            visit_b_document_id=visit_b_doc_id,
            visit_b_date=visit_b_date,
            common_analytes_count=common_cnt,
            items=comparison_items,
        )
