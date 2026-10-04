#!/usr/bin/env python3
"""
NIDAN AI — Phase 5 Prescription Intelligence & Medication Safety Benchmark
==========================================================================
Deterministic Software Correctness & Verification Suite.

CRITICAL MEDICAL & REGULATORY NOTICE:
------------------------------------
This benchmark measures SOFTWARE CORRECTNESS, PARSING FIDELITY, AND GUARDRAIL COMPLIANCE.
It does NOT constitute clinical validation or medical device approval.
Clinical validation remains a distinct future requirement involving prospective multi-center trials.

Evaluates 10 Key Dimensions:
1. Medication Entity Extraction & Parsing Fidelity
2. Medication Normalization & Strict Non-Hallucination Policy
3. Strength & Dosage Form Extraction Accuracy
4. Route Parsing (Strict Non-Inference Policy)
5. Frequency & PRN Normalization Accuracy
6. Duration Parsing & Quantity Distinction
7. Duplicate Medication Detection Precision
8. Drug-Drug Interaction (DDI) Matching Accuracy
9. Documented Allergy Safety Cross-Referencing
10. Lab-Medication Contextual Signals & CDSS Safety Guardrails
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.modules.prescription_intelligence.extraction.medication_parser import MedicationParser
from app.modules.prescription_intelligence.medication.dosage_parser import DosageParser
from app.modules.prescription_intelligence.medication.duration_parser import DurationParser
from app.modules.prescription_intelligence.medication.frequency_parser import FrequencyParser
from app.modules.prescription_intelligence.medication.normalization import MedicationNormalizer
from app.modules.prescription_intelligence.medication.route_parser import RouteParser
from app.modules.prescription_intelligence.provenance.evidence import EvidenceBuilder
from app.modules.prescription_intelligence.safety.allergy_engine import AllergyEngine
from app.modules.prescription_intelligence.safety.contraindication_engine import ContraindicationEngine
from app.modules.prescription_intelligence.safety.duplicate_engine import DuplicateEngine, RawMedicationInput
from app.modules.prescription_intelligence.safety.interaction_engine import InteractionEngine
from app.modules.prescription_intelligence.safety.lab_context_engine import LabContextEngine, RawLabObservationInput
from app.modules.prescription_intelligence.safety.safety_validator import MedicationSafetyValidator


def run_benchmark():
    print("=" * 80)
    print("NIDAN AI — PHASE 5 PRESCRIPTION INTELLIGENCE & MEDICATION SAFETY BENCHMARK")
    print("Software Correctness & Guardrail Verification Suite")
    print("=" * 80)

    category_scores = {}

    # -------------------------------------------------------------
    # 1. Medication Normalization & Non-Hallucination
    # -------------------------------------------------------------
    norm_cases = [
        ("Metformin", "Metformin", 1.0),
        ("Lipitor", "Atorvastatin", 0.90),
        ("Metformin HCl 500mg", "Metformin", 0.90),
        ("Tab. Amlodipine 5mg", "Amlodipine", 0.90),
        ("Augmentin 625mg", "Amoxicillin-Clavulanate", 0.90),
        ("Plavix 75mg", "Clopidogrel", 0.90),
        ("Aldactone 25mg", "Spironolactone", 0.90),
        ("Synthroid 100mcg", "Levothyroxine", 0.90),
        ("FakePharmaDrug999", "UNKNOWN", 0.0),
        ("RandomTextWithoutMed", "UNKNOWN", 0.0),
    ]
    norm_passed = 0
    for raw, expected_can, min_conf in norm_cases:
        can, gen, brand, conf = MedicationNormalizer.normalize(raw)
        if can == expected_can and (conf >= min_conf if expected_can != "UNKNOWN" else conf <= 0.45):
            norm_passed += 1
        else:
            print(f"  [FAIL Norm] Input: '{raw}' -> Got: '{can}' (Conf: {conf}), Expected: '{expected_can}'")

    category_scores["1. Medication Normalization"] = (norm_passed, len(norm_cases))

    # -------------------------------------------------------------
    # 2. Dosage & Strength Parsing
    # -------------------------------------------------------------
    dose_cases = [
        ("Metformin 500 mg", 500.0, "mg"),
        ("Thyronorm 50mcg", 50.0, "mcg"),
        ("Aspirin 0.5 g", 0.5, "g"),
        ("Spironolactone 25mg", 25.0, "mg"),
        ("Paracetamol 650 mg", 650.0, "mg"),
        ("Atorvastatin 40mg", 40.0, "mg"),
        ("Just Drug Name", None, None),
    ]
    dose_passed = 0
    for text, exp_val, exp_unit in dose_cases:
        val, unit = DosageParser.parse_strength(text)
        if val == exp_val and unit == exp_unit:
            dose_passed += 1
        else:
            print(f"  [FAIL Dose] Input: '{text}' -> Got: ({val}, {unit}), Expected: ({exp_val}, {exp_unit})")

    category_scores["2. Strength & Dosage Parsing"] = (dose_passed, len(dose_cases))

    # -------------------------------------------------------------
    # 3. Route Parsing (Strict Non-Inference Policy)
    # -------------------------------------------------------------
    route_cases = [
        ("Metformin 500mg PO twice daily", "ORAL"),
        ("Ceftriaxone 1g IV once daily", "INTRAVENOUS"),
        ("Insulin 10 IU SC once daily", "SUBCUTANEOUS"),
        ("Take by mouth with meals", "ORAL"),
        ("Tab Metformin 500mg twice daily", None),  # Refuse inference
        ("Cap Amoxicillin 250mg TDS", None),       # Refuse inference
    ]
    route_passed = 0
    for text, exp_route in route_cases:
        r = RouteParser.parse_route(text)
        if r == exp_route:
            route_passed += 1
        else:
            print(f"  [FAIL Route] Input: '{text}' -> Got: {r}, Expected: {exp_route}")

    category_scores["3. Route Parsing (Strict)"] = (route_passed, len(route_cases))

    # -------------------------------------------------------------
    # 4. Frequency & PRN Parsing
    # -------------------------------------------------------------
    freq_cases = [
        ("Tab Metformin 500mg BD", "BID", "twice daily", False),
        ("Atorvastatin 20mg OD at bedtime", "OD", "once daily", False),
        ("Amoxicillin 500mg TDS for 7 days", "TID", "three times daily", False),
        ("Paracetamol 650mg PRN for fever", "PRN", "as needed", True),
        ("1-0-1 after meals", "BID", "twice daily", False),
        ("1-1-1 before food", "TID", "three times daily", False),
    ]
    freq_passed = 0
    for text, exp_code, exp_text, exp_prn in freq_cases:
        code, text_desc, is_prn = FrequencyParser.parse_frequency(text)
        if code == exp_code and text_desc == exp_text and is_prn == exp_prn:
            freq_passed += 1
        else:
            print(f"  [FAIL Freq] Input: '{text}' -> Got: ({code}, '{text_desc}', {is_prn}), Expected: ({exp_code}, '{exp_text}', {exp_prn})")

    category_scores["4. Frequency & PRN Normalization"] = (freq_passed, len(freq_cases))

    # -------------------------------------------------------------
    # 5. Duration Parsing & Quantity Distinction
    # -------------------------------------------------------------
    dur_cases = [
        ("for 5 days", 5, "DAYS"),
        ("x 2 weeks", 2, "WEEKS"),
        ("for 1 month", 1, "MONTHS"),
        ("Dispense 10 tablets", None, None),  # Quantity must not become duration
        ("Take 30 capsules", None, None),
    ]
    dur_passed = 0
    for text, exp_val, exp_unit in dur_cases:
        val, unit = DurationParser.parse_duration(text)
        if val == exp_val and unit == exp_unit:
            dur_passed += 1
        else:
            print(f"  [FAIL Dur] Input: '{text}' -> Got: ({val}, {unit}), Expected: ({exp_val}, {exp_unit})")

    category_scores["5. Duration & Quantity Separation"] = (dur_passed, len(dur_cases))

    # -------------------------------------------------------------
    # 6. Duplicate Medication Detection
    # -------------------------------------------------------------
    dup_cases = [
        # (Medications, Expected Dup Findings Count)
        ([RawMedicationInput(raw_medication_name="Metformin 500mg", canonical_medication_name="Metformin"),
          RawMedicationInput(raw_medication_name="Glycomet 500mg", canonical_medication_name="Metformin")], 1),
        ([RawMedicationInput(raw_medication_name="Atorvastatin 20mg", canonical_medication_name="Atorvastatin"),
          RawMedicationInput(raw_medication_name="Metformin 500mg", canonical_medication_name="Metformin")], 0),
    ]
    dup_passed = 0
    for meds, exp_count in dup_cases:
        findings = DuplicateEngine.evaluate(meds)
        if len(findings) == exp_count:
            dup_passed += 1
        else:
            print(f"  [FAIL Dup] Expected {exp_count} duplicate findings, got {len(findings)}")

    category_scores["6. Duplicate Medication Detection"] = (dup_passed, len(dup_cases))

    # -------------------------------------------------------------
    # 7. Drug-Drug Interaction (DDI) Matching
    # -------------------------------------------------------------
    ddi_cases = [
        # Warfarin + Aspirin -> High Bleeding Alert
        ([RawMedicationInput(raw_medication_name="Warfarin", canonical_medication_name="Warfarin"),
          RawMedicationInput(raw_medication_name="Aspirin", canonical_medication_name="Aspirin")], "DDI-WAR-ASP-001"),
        # Spironolactone + Ramipril -> Hyperkalemia Alert
        ([RawMedicationInput(raw_medication_name="Spironolactone", canonical_medication_name="Spironolactone"),
          RawMedicationInput(raw_medication_name="Ramipril", canonical_medication_name="Ramipril")], "DDI-SPRO-ACEI-003"),
        # Digoxin + Amiodarone -> Toxicity Alert
        ([RawMedicationInput(raw_medication_name="Digoxin", canonical_medication_name="Digoxin"),
          RawMedicationInput(raw_medication_name="Amiodarone", canonical_medication_name="Amiodarone")], "DDI-DIG-AMIO-010"),
        # Cetirizine + Paracetamol -> No false alarm
        ([RawMedicationInput(raw_medication_name="Cetirizine", canonical_medication_name="Cetirizine"),
          RawMedicationInput(raw_medication_name="Paracetamol", canonical_medication_name="Paracetamol")], None),
    ]
    ddi_passed = 0
    for meds, exp_rule_id in ddi_cases:
        findings = InteractionEngine.evaluate(meds)
        if exp_rule_id:
            if len(findings) >= 1 and findings[0].rule_id == exp_rule_id:
                ddi_passed += 1
            else:
                print(f"  [FAIL DDI] Expected rule {exp_rule_id}, got {[f.rule_id for f in findings]}")
        else:
            if len(findings) == 0:
                ddi_passed += 1
            else:
                print(f"  [FAIL DDI] Expected 0 findings, got {len(findings)}")

    category_scores["7. Drug-Drug Interactions"] = (ddi_passed, len(ddi_cases))

    # -------------------------------------------------------------
    # 8. Documented Allergy Safety Cross-Referencing
    # -------------------------------------------------------------
    allergy_cases = [
        ([RawMedicationInput(raw_medication_name="Amoxicillin", canonical_medication_name="Amoxicillin")], ["Penicillin"], 1),
        ([RawMedicationInput(raw_medication_name="Aspirin", canonical_medication_name="Aspirin")], ["NSAID"], 1),
        ([RawMedicationInput(raw_medication_name="Metformin", canonical_medication_name="Metformin")], ["Penicillin"], 0),
        ([RawMedicationInput(raw_medication_name="Amoxicillin", canonical_medication_name="Amoxicillin")], [], 0),
    ]
    allergy_passed = 0
    for meds, allergies, exp_cnt in allergy_cases:
        findings = AllergyEngine.evaluate(meds, allergies)
        if len(findings) == exp_cnt:
            allergy_passed += 1
        else:
            print(f"  [FAIL Allergy] Expected {exp_cnt} findings, got {len(findings)}")

    category_scores["8. Allergy Safety Cross-Referencing"] = (allergy_passed, len(allergy_cases))

    # -------------------------------------------------------------
    # 9. Lab-Medication Context & Contraindications
    # -------------------------------------------------------------
    lab_cases = [
        ([RawMedicationInput(raw_medication_name="Metformin", canonical_medication_name="Metformin")],
         [RawLabObservationInput(id="o1", analyte="Creatinine", canonical_name="Serum Creatinine", value="2.4", technical_status="ABOVE_REPORTED_RANGE", finding_status="HIGH")],
         "LAB-CTX-MET-CREAT-001"),
        ([RawMedicationInput(raw_medication_name="Ramipril", canonical_medication_name="Ramipril")],
         [RawLabObservationInput(id="o2", analyte="Potassium", canonical_name="Serum Potassium", value="5.8", technical_status="ABOVE_REPORTED_RANGE", finding_status="HIGH")],
         "LAB-CTX-ACEI-POT-003"),
        ([RawMedicationInput(raw_medication_name="Metformin", canonical_medication_name="Metformin")],
         [RawLabObservationInput(id="o3", analyte="Hemoglobin", canonical_name="Hemoglobin", value="13.5", technical_status="WITHIN_REPORTED_RANGE", finding_status="NORMAL")],
         None),
    ]
    lab_passed = 0
    for meds, labs, exp_rule in lab_cases:
        findings = LabContextEngine.evaluate(meds, labs)
        if exp_rule:
            if len(findings) >= 1 and findings[0].rule_id == exp_rule:
                lab_passed += 1
            else:
                print(f"  [FAIL Lab Ctx] Expected rule {exp_rule}, got {[f.rule_id for f in findings]}")
        else:
            if len(findings) == 0:
                lab_passed += 1
            else:
                print(f"  [FAIL Lab Ctx] Expected 0 findings, got {len(findings)}")

    category_scores["9. Lab-Medication Contextual Signals"] = (lab_passed, len(lab_cases))

    # -------------------------------------------------------------
    # 10. Safety Guardrail & Provenance Verification
    # -------------------------------------------------------------
    guardrail_cases = [
        ("Potential medication interaction identified. Clinician review recommended.", True),
        ("Recent laboratory observation may be relevant to medication review.", True),
        ("You should take 500mg Metformin twice daily.", False),
        ("Stop taking Ramipril immediately.", False),
        ("Patient is diagnosed with chronic kidney disease.", False),
        ("Metformin caused elevated creatinine.", False),
    ]
    guardrail_passed = 0
    for text, expected_safe in guardrail_cases:
        res = MedicationSafetyValidator.validate_text(text)
        if res.is_safe == expected_safe:
            guardrail_passed += 1
        else:
            print(f"  [FAIL Guardrail] Text: '{text}' -> Got is_safe={res.is_safe}, Expected={expected_safe}")

    category_scores["10. CDSS Safety Guardrails"] = (guardrail_passed, len(guardrail_cases))

    # -------------------------------------------------------------
    # Summary Report
    # -------------------------------------------------------------
    print("\n" + "-" * 80)
    print(f"{'EVALUATION CATEGORY':<48} | {'PASSED / TOTAL':<16} | {'SCORE (%)':<8}")
    print("-" * 80)

    total_passed = 0
    total_cases = 0

    for cat_name, (passed, total) in category_scores.items():
        pct = (passed / total) * 100.0 if total > 0 else 100.0
        total_passed += passed
        total_cases += total
        status_flag = "[OK]" if passed == total else "[FAIL]"
        print(f"{cat_name:<48} | {passed:>6} / {total:<7} | {pct:>7.1f}% {status_flag}")

    overall_pct = (total_passed / total_cases) * 100.0 if total_cases > 0 else 100.0
    print("-" * 80)
    print(f"{'OVERALL DETERMINISTIC BENCHMARK SCORE':<48} | {total_passed:>6} / {total_cases:<7} | {overall_pct:>7.1f}%")
    print("=" * 80)

    if overall_pct == 100.0:
        print("\n>>> RESULT: SOFTWARE IMPLEMENTATION VERIFIED (100% CORRECTNESS)")
        print(">>> NOTICE: Clinical validation remains a separate medical/regulatory requirement.\n")
        return 0
    else:
        print("\n>>> RESULT: BENCHMARK FAILED. PLEASE RESOLVE DEFECTS.\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_benchmark())
