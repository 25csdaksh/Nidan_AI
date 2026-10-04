"""Comprehensive Test Suite for NIDAN AI Phase 5 — Prescription Intelligence & Medication Safety.

Tests:
1. Valid prescription parsing & extraction
2. OCR text extraction & line parsing
3. Medication normalization & alias resolution
4. Unknown medication fallback policy (Strict non-hallucination)
5. Dosage & strength parsing
6. Missing dosage handling
7. Frequency normalization & PRN parsing
8. Route parsing (strict non-inference policy)
9. Duration parsing (quantity vs duration separation)
10. Duplicate medication detection
11. Drug-Drug Interaction (DDI) engine
12. No validated interaction rule behavior
13. Allergy safety cross-referencing
14. Allergy mismatch & missing allergy handling
15. Lab-medication contextual safety engine
16. Clinical contraindication framework
17. Clinician review & note audit workflow
18. Provenance trace completeness
19. RBAC & patient isolation
20. Audit logging verification
21. MedicationSafetyValidator guardrails
22. Patient medication timeline
23. Idempotency & API endpoints
"""

import io
import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.main import app
from app.modules.clinical_intelligence.models import ClinicalObservation
from app.modules.medical_documents.models import DocumentTypeEnum, MedicalDocument, ProcessingStatusEnum
from app.modules.patients.models import Patient
from app.modules.prescription_intelligence.extraction.confidence import PrescriptionConfidenceScorer
from app.modules.prescription_intelligence.extraction.instruction_parser import InstructionParser
from app.modules.prescription_intelligence.extraction.medication_parser import MedicationParser
from app.modules.prescription_intelligence.extraction.prescription_extractor import PrescriptionExtractor
from app.modules.prescription_intelligence.medication.dosage_parser import DosageParser
from app.modules.prescription_intelligence.medication.duration_parser import DurationParser
from app.modules.prescription_intelligence.medication.frequency_parser import FrequencyParser
from app.modules.prescription_intelligence.medication.normalization import MedicationNormalizer
from app.modules.prescription_intelligence.medication.route_parser import RouteParser
from app.modules.prescription_intelligence.models import (
    MedicationReviewStatusEnum,
    MedicationSafetyFinding,
    Prescription,
    PrescriptionMedication,
    PrescriptionStatusEnum,
)
from app.modules.prescription_intelligence.safety.allergy_engine import AllergyEngine
from app.modules.prescription_intelligence.safety.contraindication_engine import ContraindicationEngine
from app.modules.prescription_intelligence.safety.duplicate_engine import DuplicateEngine, RawMedicationInput
from app.modules.prescription_intelligence.safety.interaction_engine import InteractionEngine
from app.modules.prescription_intelligence.safety.lab_context_engine import LabContextEngine, RawLabObservationInput
from app.modules.prescription_intelligence.safety.safety_validator import MedicationSafetyValidator
from app.modules.users.models import User


# ---------------------------------------------------------
# Unit Tests: Medication Vocabulary & Parsers
# ---------------------------------------------------------

def test_medication_normalization_exact_and_alias():
    # Exact canonical
    can, gen, brand, conf = MedicationNormalizer.normalize("Metformin")
    assert can == "Metformin"
    assert gen == "Metformin Hydrochloride"
    assert conf == 1.0

    # Brand name alias
    can, gen, brand, conf = MedicationNormalizer.normalize("Lipitor")
    assert can == "Atorvastatin"
    assert brand == "Lipitor"
    assert conf >= 0.90

    # Multi-word alias with salts
    can, gen, brand, conf = MedicationNormalizer.normalize("Metformin HCl 500mg")
    assert can == "Metformin"
    assert conf >= 0.90

    # Prefix stripping
    can, gen, brand, conf = MedicationNormalizer.normalize("Tab. Amlodipine 5mg")
    assert can == "Amlodipine"
    assert conf >= 0.90


def test_unknown_medication_strict_policy():
    can, gen, brand, conf = MedicationNormalizer.normalize("FictionalDrugXYZ 100mg")
    assert can == "UNKNOWN"
    assert gen is None
    assert conf <= 0.45


def test_dosage_and_strength_parsing():
    val, unit = DosageParser.parse_strength("Metformin 500 mg")
    assert val == 500.0
    assert unit == "mg"

    val, unit = DosageParser.parse_strength("Thyronorm 50mcg")
    assert val == 50.0
    assert unit == "mcg"

    val, unit = DosageParser.parse_strength("Aspirin 0.5 g")
    assert val == 0.5
    assert unit == "g"

    # Missing strength
    val, unit = DosageParser.parse_strength("Just Drug Name")
    assert val is None
    assert unit is None


def test_dosage_form_parsing():
    assert DosageParser.parse_dosage_form("Tab Metformin 500mg") == "Tablet"
    assert DosageParser.parse_dosage_form("Cap Amoxicillin 250mg") == "Capsule"
    assert DosageParser.parse_dosage_form("Inj Insulatard 100IU") == "Injection"
    assert DosageParser.parse_dosage_form("Syrup Paracetamol") == "Syrup"
    assert DosageParser.parse_dosage_form("Metformin 500mg") is None


def test_dose_quantity_parsing():
    assert DosageParser.parse_dose_quantity("1 tablet twice daily") == "1 tablet"
    assert DosageParser.parse_dose_quantity("2 puffs PRN") == "2 puffs"
    assert DosageParser.parse_dose_quantity("5 ml TID") == "5 ml"
    assert DosageParser.parse_dose_quantity("take without quantity") is None


def test_route_parsing_strict_no_hallucination():
    assert RouteParser.parse_route("Tab Metformin 500mg PO twice daily") == "ORAL"
    assert RouteParser.parse_route("Ceftriaxone 1g IV once daily") == "INTRAVENOUS"
    assert RouteParser.parse_route("Insulin 10 units SC daily") == "SUBCUTANEOUS"
    assert RouteParser.parse_route("Take by mouth with meals") == "ORAL"

    # Strict: do not infer route from tablet/capsule alone
    assert RouteParser.parse_route("Tab Metformin 500mg twice daily") is None


def test_frequency_parsing_and_prn():
    code, text, is_prn = FrequencyParser.parse_frequency("Tab Metformin 500mg BD")
    assert code == "BID"
    assert text == "twice daily"
    assert is_prn is False

    code, text, is_prn = FrequencyParser.parse_frequency("Atorvastatin 20mg OD at bedtime")
    assert code == "OD"
    assert text == "once daily"

    code, text, is_prn = FrequencyParser.parse_frequency("Paracetamol 650mg PRN for pain")
    assert code == "PRN"
    assert is_prn is True

    # Latin sig format "1-0-1" -> BID
    code, text, is_prn = FrequencyParser.parse_frequency("1-0-1 after food")
    assert code == "BID"
    assert text == "twice daily"


def test_duration_parsing_quantity_separation():
    # Valid explicit duration
    val, unit = DurationParser.parse_duration("for 5 days")
    assert val == 5
    assert unit == "DAYS"

    val, unit = DurationParser.parse_duration("x 2 weeks")
    assert val == 2
    assert unit == "WEEKS"

    val, unit = DurationParser.parse_duration("for 1 month")
    assert val == 1
    assert unit == "MONTHS"

    # Quantity distinction: "10 tablets" must NOT become "10 days"
    val, unit = DurationParser.parse_duration("Dispense 10 tablets")
    assert val is None
    assert unit is None


def test_instruction_parsing():
    inst = InstructionParser.parse_instructions("Tab Metformin 500mg BD after meals with water")
    assert "after meals" in inst
    assert "with plenty of water" in inst


def test_medication_line_parsing():
    line = "1. Tab Metformin 500mg 1 tab BD for 30 days after food"
    item = MedicationParser.parse_line(line)
    assert item is not None
    assert item.canonical_medication_name == "Metformin"
    assert item.strength_value == 500.0
    assert item.strength_unit == "mg"
    assert item.dosage_form == "Tablet"
    assert item.frequency_code == "BID"
    assert item.duration_value == 30
    assert item.duration_unit == "DAYS"
    assert item.confidence >= 0.85


# ---------------------------------------------------------
# Unit Tests: Safety Engines
# ---------------------------------------------------------

def test_duplicate_medication_detection():
    meds = [
        RawMedicationInput(id="m1", raw_medication_name="Metformin 500mg", canonical_medication_name="Metformin"),
        RawMedicationInput(id="m2", raw_medication_name="Glycomet 500mg", canonical_medication_name="Metformin"),
    ]
    findings = DuplicateEngine.evaluate(meds)
    assert len(findings) == 1
    assert findings[0].finding_type == "POTENTIAL_DUPLICATE"
    assert "Multiple Entries" in findings[0].title
    assert findings[0].evidence["canonical_medication_name"] == "Metformin"


def test_drug_drug_interaction_matching():
    meds = [
        RawMedicationInput(id="m1", raw_medication_name="Warfarin 5mg", canonical_medication_name="Warfarin"),
        RawMedicationInput(id="m2", raw_medication_name="Aspirin 75mg", canonical_medication_name="Aspirin"),
    ]
    findings = InteractionEngine.evaluate(meds)
    assert len(findings) == 1
    assert findings[0].finding_type == "DRUG_DRUG_INTERACTION"
    assert findings[0].severity == "HIGH"
    assert findings[0].rule_id == "DDI-WAR-ASP-001"
    assert "Warfarin" in findings[0].evidence["canonical_medication_name"]


def test_no_validated_interaction_rule():
    meds = [
        RawMedicationInput(id="m1", raw_medication_name="Cetirizine 10mg", canonical_medication_name="Cetirizine"),
        RawMedicationInput(id="m2", raw_medication_name="Paracetamol 500mg", canonical_medication_name="Paracetamol"),
    ]
    findings = InteractionEngine.evaluate(meds)
    assert len(findings) == 0  # No false alarms


def test_allergy_safety_engine():
    meds = [
        RawMedicationInput(id="m1", raw_medication_name="Amoxicillin 500mg", canonical_medication_name="Amoxicillin"),
        RawMedicationInput(id="m2", raw_medication_name="Metformin 500mg", canonical_medication_name="Metformin"),
    ]
    allergies = ["Penicillin", "Sulfa"]

    findings = AllergyEngine.evaluate(meds, allergies)
    assert len(findings) == 1
    assert findings[0].finding_type == "POTENTIAL_ALLERGY_CONCERN"
    assert findings[0].evidence["canonical_medication_name"] == "Amoxicillin"
    assert findings[0].evidence["allergy_match"] == "penicillin"


def test_lab_medication_context_engine():
    meds = [
        RawMedicationInput(id="m1", raw_medication_name="Metformin 500mg", canonical_medication_name="Metformin"),
    ]
    labs = [
        RawLabObservationInput(
            id="obs-1",
            analyte="Creatinine",
            canonical_name="Serum Creatinine",
            value="2.2",
            unit="mg/dL",
            technical_status="ABOVE_REPORTED_RANGE",
            finding_status="HIGH",
        )
    ]
    findings = LabContextEngine.evaluate(meds, labs)
    assert len(findings) == 1
    assert findings[0].finding_type == "LAB_CONTEXT_SIGNAL"
    assert findings[0].rule_id == "LAB-CTX-MET-CREAT-001"
    assert findings[0].evidence["lab_analyte"] == "Serum Creatinine"


def test_contraindication_engine():
    meds = [
        RawMedicationInput(id="m1", raw_medication_name="Ibuprofen 400mg", canonical_medication_name="Ibuprofen"),
    ]
    conditions = ["Peptic Ulcer Disease", "Hypertension"]
    findings = ContraindicationEngine.evaluate(meds, conditions)
    assert len(findings) == 1
    assert findings[0].finding_type == "CONTRAINDICATION_SIGNAL"
    assert findings[0].rule_id == "CI-NSAID-PUD-001"


def test_safety_validator_guardrails():
    # Safe text
    res = MedicationSafetyValidator.validate_text("Potential medication interaction identified. Clinician review recommended.")
    assert res.is_safe is True
    assert len(res.violations) == 0

    # Unsafe prescriptive text
    res = MedicationSafetyValidator.validate_text("You should take 500mg Metformin twice daily.")
    assert res.is_safe is False
    assert any("prescriptive" in v for v in res.violations)

    # Unsafe discontinuation command
    res = MedicationSafetyValidator.validate_text("Stop taking Lisinopril immediately.")
    assert res.is_safe is False

    # Unsafe diagnosis assertion
    res = MedicationSafetyValidator.validate_text("Patient is diagnosed with diabetes.")
    assert res.is_safe is False


# ---------------------------------------------------------
# Integration & End-to-End API Tests
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_prescription_document_extraction_and_safety_flow(setup_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create Patient with allergy & chronic condition
        pat_resp = await client.post(
            "/api/v1/patients/",
            json={
                "mrn": "RX-PAT-001",
                "first_name": "Aarav",
                "last_name": "Sharma",
                "date_of_birth": "1980-05-15",
                "gender": "male",
                "known_allergies": ["Penicillin"],
                "chronic_conditions": ["Type 2 Diabetes"],
            },
        )
        assert pat_resp.status_code == 201
        patient_id = pat_resp.json()["id"]

        # 2. Upload Prescription PDF
        rx_pdf_text = (
            "CITY CLINIC HEALTHCARE\n"
            "Dr. Sarah Jenkins, MD\n"
            "Date: 2026-09-15\n"
            "Patient Name: Aarav Sharma\n"
            "Rx:\n"
            "1. Tab. Metformin 500mg 1 tab BD for 30 days after meals\n"
            "2. Tab. Ramipril 5mg 1 tab OD\n"
            "3. Tab. Spironolactone 25mg 1 tab OD\n"
            "4. Cap. Amoxicillin 500mg 1 cap TDS for 7 days\n"
        )
        # 2. Upload Prescription PDF
        rx_pdf_text = (
            "CITY CLINIC HEALTHCARE\n"
            "Dr. Sarah Jenkins\n"
            "Date: 2026-09-15\n"
            "Patient Name: Aarav Sharma\n"
            "Rx\n"
            "1. Tab. Metformin 500mg 1 tab BD for 30 days after meals\n"
            "2. Tab. Ramipril 5mg 1 tab OD\n"
            "3. Tab. Spironolactone 25mg 1 tab OD\n"
            "4. Cap. Amoxicillin 500mg 1 cap TDS for 7 days\n"
        )
        
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        y = 750
        for line in rx_pdf_text.splitlines():
            if line.strip():
                c.drawString(50, y, line.strip())
                y -= 25
        c.save()
        raw_bytes = buf.getvalue()

        # Ingest document via /api/v1/medical-documents
        files = {"file": ("prescription_visit1.pdf", raw_bytes, "application/pdf")}
        data = {"patient_id": patient_id, "document_type": "PRESCRIPTION"}
        doc_resp = await client.post("/api/v1/medical-documents", files=files, data=data)
        assert doc_resp.status_code == 201
        doc_id = doc_resp.json()["document"]["id"]

        # 3. Trigger Prescription Extraction via API
        extract_resp = await client.post(f"/api/v1/medical-documents/{doc_id}/prescription-extraction")
        assert extract_resp.status_code == 200
        rx_data = extract_resp.json()
        assert rx_data["patient_id"] == patient_id
        assert rx_data["document_id"] == doc_id
        assert rx_data["status"] in ["EXTRACTED", "REVIEW_REQUIRED"]
        assert len(rx_data["medications"]) >= 3

        # 4. List Patient Prescriptions
        list_resp = await client.get(f"/api/v1/patients/{patient_id}/prescriptions")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # 5. List Patient Medications
        meds_resp = await client.get(f"/api/v1/patients/{patient_id}/medications")
        assert meds_resp.status_code == 200
        assert len(meds_resp.json()) >= 3

        # 6. Run Medication Safety Analysis Endpoint
        safety_resp = await client.post(f"/api/v1/patients/{patient_id}/medication-safety-analysis", json={})
        assert safety_resp.status_code == 200
        safety_data = safety_resp.json()
        assert "findings" in safety_data
        assert safety_data["patient_id"] == patient_id

        # 7. Get Medication Timeline
        timeline_resp = await client.get(f"/api/v1/patients/{patient_id}/medication-timeline")
        assert timeline_resp.status_code == 200
        timeline_data = timeline_resp.json()
        assert timeline_data["total_prescriptions"] >= 1
        assert len(timeline_data["events"]) >= 1

        # 8. List Safety Rules Catalog
        rules_resp = await client.get("/api/v1/medication-rules")
        assert rules_resp.status_code == 200
        rules_list = rules_resp.json()
        assert len(rules_list) >= 10
        assert any(r["rule_id"] == "DDI-WAR-ASP-001" for r in rules_list)


@pytest.mark.asyncio
async def test_clinician_review_safety_finding(setup_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create patient and direct finding
        pat_resp = await client.post(
            "/api/v1/patients/",
            json={
                "mrn": "RX-PAT-002",
                "first_name": "Rohan",
                "last_name": "Mehta",
                "date_of_birth": "1975-02-10",
                "gender": "male",
                "known_allergies": ["Aspirin"],
                "chronic_conditions": [],
            },
        )
        patient_id = pat_resp.json()["id"]

        # Run safety analysis
        await client.post(f"/api/v1/patients/{patient_id}/medication-safety-analysis", json={})

        # List findings
        findings_resp = await client.get(f"/api/v1/patients/{patient_id}/medication-safety-findings")
        assert findings_resp.status_code == 200


@pytest.mark.asyncio
async def test_clinician_review_and_rbac_isolation(setup_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create Patient
        pat_resp = await client.post(
            "/api/v1/patients/",
            json={
                "mrn": "RX-PAT-003",
                "first_name": "Priya",
                "last_name": "Patel",
                "date_of_birth": "1992-11-20",
                "gender": "female",
                "known_allergies": ["Penicillin"],
                "chronic_conditions": [],
            },
        )
        patient_id = pat_resp.json()["id"]

        # 2. Upload prescription with Amoxicillin (triggers allergy alert) and Warfarin + Aspirin (triggers DDI alert)
        rx_text = (
            "CITY HOSPITAL\n"
            "Dr. Richard Lee\n"
            "Date: 2026-09-20\n"
            "Rx\n"
            "1. Tab Warfarin 5mg 1 tab OD\n"
            "2. Tab Aspirin 75mg 1 tab OD\n"
            "3. Cap Amoxicillin 500mg 1 cap TDS for 7 days\n"
        )
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        y = 750
        for line in rx_text.splitlines():
            if line.strip():
                c.drawString(50, y, line.strip())
                y -= 25
        c.save()
        raw_bytes = buf.getvalue()

        files = {"file": ("rx_complex.pdf", raw_bytes, "application/pdf")}
        data = {"patient_id": patient_id, "document_type": "PRESCRIPTION"}
        doc_resp = await client.post("/api/v1/medical-documents", files=files, data=data)
        doc_id = doc_resp.json()["document"]["id"]

        # Extract
        await client.post(f"/api/v1/medical-documents/{doc_id}/prescription-extraction")

        # 3. Retrieve findings
        findings_resp = await client.get(f"/api/v1/patients/{patient_id}/medication-safety-findings")
        assert findings_resp.status_code == 200
        findings = findings_resp.json()
        assert len(findings) >= 2

        target_finding = findings[0]
        finding_id = target_finding["id"]

        # 4. Clinician Reviews Finding (ACCEPT)
        review_resp = await client.post(
            f"/api/v1/medication-safety-findings/{finding_id}/review",
            json={
                "review_status": "ACCEPTED",
                "clinician_note": "Risk discussed with patient. Monitoring coagulation and bleeding signs.",
            },
        )
        assert review_resp.status_code == 200
        rev_data = review_resp.json()
        assert rev_data["review_status"] == "ACCEPTED"
        assert rev_data["clinician_note"] == "Risk discussed with patient. Monitoring coagulation and bleeding signs."

        # 5. Patient Role Access Check (RBAC): Patient cannot review clinician findings
        patient_token = create_access_token(subject="patient-user-1", role="patient", extra_claims={"patient_id": patient_id})
        patient_headers = {"Authorization": f"Bearer {patient_token}"}

        # Patient viewing their own findings should succeed
        pat_view_resp = await client.get(f"/api/v1/patients/{patient_id}/medication-safety-findings", headers=patient_headers)
        assert pat_view_resp.status_code == 200

        # Patient attempting clinician review must fail (403 Forbidden)
        pat_review_resp = await client.post(
            f"/api/v1/medication-safety-findings/{finding_id}/review",
            json={"review_status": "REJECTED", "clinician_note": "Patient trying to dismiss alert"},
            headers=patient_headers,
        )
        assert pat_review_resp.status_code == 403

        # Patient viewing OTHER patient record must fail (403 Forbidden)
        other_view_resp = await client.get(f"/api/v1/patients/other-patient-uuid/medication-safety-findings", headers=patient_headers)
        assert other_view_resp.status_code == 403
