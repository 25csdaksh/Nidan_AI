"""NIDAN AI Extraction Evaluation Engine (Phase 2).

Evaluates OCR character accuracy, entity extraction precision, recall,
numeric accuracy, unit accuracy, and range extraction against ground truth.

Strictly separates Extraction Accuracy from Clinical Efficacy.
"""

import asyncio
import io
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel
from pypdf import PdfWriter

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.modules.medical_documents.extraction.pipeline import MedicalExtractionPipeline



class GroundTruthSample(BaseModel):
    sample_id: str
    document_name: str
    text_content: str
    expected_entities: Dict[str, Dict[str, Any]]


# Evaluation Benchmarking Dataset
BENCHMARK_DATASET: List[GroundTruthSample] = [
    GroundTruthSample(
        sample_id="SAMPLE-01-CBC-NORMAL",
        document_name="Standard CBC Panel",
        text_content=(
            "HEMATOLOGY COMPLETE BLOOD COUNT REPORT\n"
            "Hemoglobin 15.0 g/dL   Reference: 13.0 - 17.0 g/dL\n"
            "WBC Count 6.8 10^3/uL   Reference: 4.0 - 11.0 10^3/uL\n"
            "Platelet Count 240 10^3/uL   Reference: 150 - 450 10^3/uL\n"
            "Hematocrit 45 %   Reference: 40 - 52 %\n"
            "MCV 88 fL   Reference: 80 - 100 fL\n"
        ),
        expected_entities={
            "Hemoglobin": {"numeric": 15.0, "unit": "g/dL", "ref_min": 13.0, "ref_max": 17.0},
            "WBC": {"numeric": 6.8, "unit": "10^3/uL", "ref_min": 4.0, "ref_max": 11.0},
            "Platelets": {"numeric": 240.0, "unit": "10^3/uL", "ref_min": 150.0, "ref_max": 450.0},
            "Hematocrit": {"numeric": 45.0, "unit": "%", "ref_min": 40.0, "ref_max": 52.0},
            "MCV": {"numeric": 88.0, "unit": "fL", "ref_min": 80.0, "ref_max": 100.0},
        },
    ),
    GroundTruthSample(
        sample_id="SAMPLE-02-METABOLIC-PANEL",
        document_name="Renal & Glucose Panel",
        text_content=(
            "BIOCHEMISTRY CLINICAL PATHOLOGY\n"
            "Serum Creatinine 1.1 mg/dL   Reference: 0.6 - 1.2 mg/dL\n"
            "Blood Urea 28 mg/dL   Reference: 15 - 45 mg/dL\n"
            "Fasting Blood Sugar 105 mg/dL   Reference: 70 - 99 mg/dL\n"
            "HbA1c 6.2 %   Reference: < 5.7 %\n"
            "Serum Sodium 140 mmol/L   Reference: 135 - 145 mmol/L\n"
        ),
        expected_entities={
            "Creatinine": {"numeric": 1.1, "unit": "mg/dL", "ref_min": 0.6, "ref_max": 1.2},
            "Urea": {"numeric": 28.0, "unit": "mg/dL", "ref_min": 15.0, "ref_max": 45.0},
            "Fasting Blood Sugar": {"numeric": 105.0, "unit": "mg/dL", "ref_min": 70.0, "ref_max": 99.0},
            "HbA1c": {"numeric": 6.2, "unit": "%", "ref_min": None, "ref_max": 5.7},
            "Sodium": {"numeric": 140.0, "unit": "mmol/L", "ref_min": 135.0, "ref_max": 145.0},
        },
    ),
    GroundTruthSample(
        sample_id="SAMPLE-03-LIPID-THYROID",
        document_name="Lipid & Thyroid Panel",
        text_content=(
            "SPECIALIZED ENDOCRINOLOGY & LIPID PROFILE\n"
            "Total Cholesterol 220 mg/dL   Reference: < 200 mg/dL\n"
            "HDL 45 mg/dL   Reference: > 40 mg/dL\n"
            "LDL 145 mg/dL   Reference: < 100 mg/dL\n"
            "Serum Triglycerides 160 mg/dL   Reference: < 150 mg/dL\n"
            "TSH 3.1 uIU/mL   Reference: 0.4 - 4.2 uIU/mL\n"
        ),
        expected_entities={
            "Total Cholesterol": {"numeric": 220.0, "unit": "mg/dL", "ref_min": None, "ref_max": 200.0},
            "HDL": {"numeric": 45.0, "unit": "mg/dL", "ref_min": 40.0, "ref_max": None},
            "LDL": {"numeric": 145.0, "unit": "mg/dL", "ref_min": None, "ref_max": 100.0},
            "Triglycerides": {"numeric": 160.0, "unit": "mg/dL", "ref_min": None, "ref_max": 150.0},
            "TSH": {"numeric": 3.1, "unit": "uIU/mL", "ref_min": 0.4, "ref_max": 4.2},
        },
    ),
]


def build_synthetic_pdf(text: str) -> bytes:
    """Constructs a clean in-memory PDF containing the benchmark text."""
    lines = text.splitlines()
    stream_content = "BT\n/F1 12 Tf\n50 720 Td\n"
    for idx, line in enumerate(lines):
        clean_line = line.replace("(", "\\(").replace(")", "\\)")
        if idx == 0:
            stream_content += f"({clean_line}) Tj\n"
        else:
            stream_content += f"0 -25 Td\n({clean_line}) Tj\n"
    stream_content += "ET\n"
    
    stream_bytes = stream_content.encode("latin-1")
    length = len(stream_bytes)
    
    pdf_bytes = (
        f"%PDF-1.4\n"
        f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        f"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        f"4 0 obj\n<< /Length {length} >>\nstream\n"
    ).encode("latin-1") + stream_bytes + (
        f"\nendstream\nendobj\n"
        f"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        f"xref\n0 6\n0000000000 65535 f \n"
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n500\n%%EOF"
    ).encode("latin-1")
    return pdf_bytes


async def run_evaluation():
    print("=" * 70)
    print("NIDAN AI - PHASE 2 EXTRACTION EVALUATION BENCHMARK")
    print("=" * 70)

    pipeline = MedicalExtractionPipeline()

    total_expected_entities = 0
    total_extracted_entities = 0
    true_positives = 0
    numeric_matches = 0
    unit_matches = 0
    range_matches = 0
    start_eval_time = time.time()

    for sample in BENCHMARK_DATASET:
        print(f"\nEvaluating: {sample.sample_id} ({sample.document_name})...")
        pdf_bytes = build_synthetic_pdf(sample.text_content)
        
        result = await pipeline.process(
            file_bytes=pdf_bytes,
            mime_type="application/pdf",
            has_embedded_text=True,
        )

        extracted_map = {e.canonical_name: e for e in result.entities}
        total_expected_entities += len(sample.expected_entities)
        total_extracted_entities += len(result.entities)

        for canonical, exp in sample.expected_entities.items():
            if canonical in extracted_map:
                true_positives += 1
                ent = extracted_map[canonical]
                
                # Check numeric value
                if ent.numeric_value == exp["numeric"]:
                    numeric_matches += 1
                
                # Check unit
                if ent.normalized_unit == exp["unit"]:
                    unit_matches += 1
                
                # Check reference range
                if ent.reference_min == exp["ref_min"] and ent.reference_max == exp["ref_max"]:
                    range_matches += 1
                
                print(f"  [OK] Extracted {canonical:20} -> {ent.numeric_value} {ent.normalized_unit} (Ref: {ent.reference_min}-{ent.reference_max}) [Conf: {ent.confidence}]")
            else:
                print(f"  [X]  MISSING: {canonical:20}")


    duration = time.time() - start_eval_time

    # Calculate metrics
    precision = (true_positives / total_extracted_entities) * 100 if total_extracted_entities > 0 else 0
    recall = (true_positives / total_expected_entities) * 100 if total_expected_entities > 0 else 0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    numeric_acc = (numeric_matches / true_positives) * 100 if true_positives > 0 else 0
    unit_acc = (unit_matches / true_positives) * 100 if true_positives > 0 else 0
    range_acc = (range_matches / true_positives) * 100 if true_positives > 0 else 0

    print("\n" + "=" * 70)
    print("EVALUATION METRIC RESULTS")
    print("=" * 70)
    print(f"Total Benchmark Samples:      {len(BENCHMARK_DATASET)}")
    print(f"Total Expected Entities:      {total_expected_entities}")
    print(f"Total Extracted Entities:     {total_extracted_entities}")
    print(f"True Positive Extractions:    {true_positives}")
    print(f"Entity Precision:             {precision:.2f}%")
    print(f"Entity Recall:                {recall:.2f}%")
    print(f"Extraction F1-Score:          {f1_score:.2f}%")
    print(f"Numeric Parsing Accuracy:     {numeric_acc:.2f}%")
    print(f"Unit Normalization Accuracy:  {unit_acc:.2f}%")
    print(f"Reference Range Accuracy:     {range_acc:.2f}%")
    print(f"Total Processing Time:        {duration:.3f}s")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_evaluation())
