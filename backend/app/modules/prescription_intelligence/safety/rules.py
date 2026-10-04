"""Authoritative, Versioned Medication Safety Knowledge Base for NIDAN AI.

Contains curated, evidence-backed rules for:
1. Drug-Drug Interactions (DDIs)
2. Drug-Allergy Safety Concerns
3. Lab-Medication Contextual Signals
4. Clinical Contraindication Framework
5. Prescription Completeness Checks

Strict Safety Policy: All alerts are observational Clinical Decision Support (CDSS Level 1 & 2),
never autonomous diagnoses, prescriptions, or treatment recommendations.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class InteractionRuleDefinition(BaseModel):
    rule_id: str
    drug_a: str
    drug_b: str
    interaction_type: str
    severity: str  # CRITICAL, HIGH, MODERATE, LOW, INFO
    title: str
    description: str
    clinical_association: str
    evidence_source: str
    source_version: str = "2026.1"
    rule_version: str = "1.0.0"
    requires_review: bool = True
    active: bool = True


class AllergyRuleDefinition(BaseModel):
    rule_id: str
    medication: str
    allergen_class: str
    severity: str = "HIGH"
    title: str
    description: str
    evidence_source: str
    rule_version: str = "1.0.0"


class LabContextRuleDefinition(BaseModel):
    rule_id: str
    medication: str
    lab_analyte: str
    condition_status: str  # HIGH, LOW, CRITICAL_HIGH, CRITICAL_LOW, ABNORMAL
    severity: str  # HIGH, MODERATE, INFO
    title: str
    description: str
    clinical_association: str
    evidence_source: str
    rule_version: str = "1.0.0"


class ContraindicationRuleDefinition(BaseModel):
    rule_id: str
    medication: str
    condition: str
    severity: str = "HIGH"
    title: str
    description: str
    evidence_source: str
    rule_version: str = "1.0.0"


# 1. Curated Drug-Drug Interaction Rules
DRUG_INTERACTION_RULES: List[InteractionRuleDefinition] = [
    InteractionRuleDefinition(
        rule_id="DDI-WAR-ASP-001",
        drug_a="Warfarin",
        drug_b="Aspirin",
        interaction_type="PHARMACODYNAMIC_BLEEDING_RISK",
        severity="HIGH",
        title="Concurrent Anticoagulant and Antiplatelet Agent Documented",
        description="Co-prescription of Warfarin and Aspirin increases the potential risk of major bleeding complications.",
        clinical_association="Dual antithrombotic therapy warrants clinical verification of indication and bleeding risk assessment.",
        evidence_source="FDA Drug Safety / CHEST Guidelines",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-CLOP-OMEP-002",
        drug_a="Clopidogrel",
        drug_b="Omeprazole",
        interaction_type="CYP2C19_METABOLIC_INHIBITION",
        severity="MODERATE",
        title="Potential CYP2C19 Interaction Between Clopidogrel and Omeprazole",
        description="Omeprazole inhibits CYP2C19, which may reduce the metabolic conversion of Clopidogrel to its active antiplatelet form.",
        clinical_association="Consider review of gastroprotection strategy in patients requiring antiplatelet therapy.",
        evidence_source="FDA Safety Alert / ACCP Guidelines",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-SPRO-ACEI-003",
        drug_a="Spironolactone",
        drug_b="Ramipril",
        interaction_type="PHARMACODYNAMIC_HYPERKALEMIA",
        severity="HIGH",
        title="Concurrent Potassium-Sparing Diuretic and ACE Inhibitor Documented",
        description="Combining Spironolactone with Ramipril may increase the risk of hyperkalemia.",
        clinical_association="Monitoring of serum potassium and renal function is clinically recommended.",
        evidence_source="AHA/ACC Heart Failure Guidelines",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-SPRO-ENAL-004",
        drug_a="Spironolactone",
        drug_b="Enalapril",
        interaction_type="PHARMACODYNAMIC_HYPERKALEMIA",
        severity="HIGH",
        title="Concurrent Potassium-Sparing Diuretic and ACE Inhibitor Documented",
        description="Combining Spironolactone with Enalapril may increase the risk of hyperkalemia.",
        clinical_association="Monitoring of serum potassium and renal function is clinically recommended.",
        evidence_source="AHA/ACC Heart Failure Guidelines",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-SPRO-LISIN-005",
        drug_a="Spironolactone",
        drug_b="Lisinopril",
        interaction_type="PHARMACODYNAMIC_HYPERKALEMIA",
        severity="HIGH",
        title="Concurrent Potassium-Sparing Diuretic and ACE Inhibitor Documented",
        description="Combining Spironolactone with Lisinopril may increase the risk of hyperkalemia.",
        clinical_association="Monitoring of serum potassium and renal function is clinically recommended.",
        evidence_source="AHA/ACC Heart Failure Guidelines",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-SPRO-TELM-006",
        drug_a="Spironolactone",
        drug_b="Telmisartan",
        interaction_type="PHARMACODYNAMIC_HYPERKALEMIA",
        severity="HIGH",
        title="Concurrent Potassium-Sparing Diuretic and ARB Documented",
        description="Combining Spironolactone with Telmisartan may increase the risk of hyperkalemia.",
        clinical_association="Monitoring of serum potassium and renal function is clinically recommended.",
        evidence_source="AHA/ACC Heart Failure Guidelines",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-SPRO-LOS-007",
        drug_a="Spironolactone",
        drug_b="Losartan",
        interaction_type="PHARMACODYNAMIC_HYPERKALEMIA",
        severity="HIGH",
        title="Concurrent Potassium-Sparing Diuretic and ARB Documented",
        description="Combining Spironolactone with Losartan may increase the risk of hyperkalemia.",
        clinical_association="Monitoring of serum potassium and renal function is clinically recommended.",
        evidence_source="AHA/ACC Heart Failure Guidelines",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-MTX-NSAID-008",
        drug_a="Methotrexate",
        drug_b="Ibuprofen",
        interaction_type="RENAL_CLEARANCE_REDUCTION",
        severity="HIGH",
        title="Concurrent Methotrexate and NSAID Documented",
        description="NSAIDs may decrease renal clearance of Methotrexate, potentially elevating methotrexate serum levels.",
        clinical_association="Clinical monitoring of complete blood count and renal function is recommended.",
        evidence_source="EULAR Recommendations / FDA Package Insert",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-MTX-DICLO-009",
        drug_a="Methotrexate",
        drug_b="Diclofenac",
        interaction_type="RENAL_CLEARANCE_REDUCTION",
        severity="HIGH",
        title="Concurrent Methotrexate and NSAID Documented",
        description="Diclofenac may reduce renal elimination of Methotrexate, increasing potential toxicity.",
        clinical_association="Clinical correlation and laboratory monitoring recommended.",
        evidence_source="EULAR Recommendations / FDA Package Insert",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-DIG-AMIO-010",
        drug_a="Digoxin",
        drug_b="Amiodarone",
        interaction_type="P_GLYCOPROTEIN_INHIBITION",
        severity="HIGH",
        title="Concurrent Digoxin and Amiodarone Documented",
        description="Amiodarone inhibits P-glycoprotein and renal elimination of Digoxin, frequently doubling digoxin concentrations.",
        clinical_association="Monitoring of serum digoxin levels and electrocardiographic correlation recommended.",
        evidence_source="ESC/AHA Arrhythmia Guidelines",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-CIPRO-THEO-011",
        drug_a="Ciprofloxacin",
        drug_b="Theophylline",
        interaction_type="CYP1A2_INHIBITION",
        severity="HIGH",
        title="Concurrent Ciprofloxacin and Theophylline Documented",
        description="Ciprofloxacin inhibits the CYP1A2 metabolism of Theophylline, which may increase theophylline levels.",
        clinical_association="Therapeutic drug monitoring and clinical correlation recommended.",
        evidence_source="FDA Drug Safety Communications",
    ),
    InteractionRuleDefinition(
        rule_id="DDI-STAT-FIB-012",
        drug_a="Atorvastatin",
        drug_b="Gemfibrozil",
        interaction_type="GLUCURONIDATION_INHIBITION",
        severity="HIGH",
        title="Concurrent Statin and Fibrate Documented",
        description="Co-administration of Atorvastatin and Gemfibrozil increases statin exposure and risk of myopathy.",
        clinical_association="Clinical monitoring of muscle symptoms and CK levels recommended if combination is used.",
        evidence_source="ACC/AHA Cholesterol Guidelines",
    ),
]

# 2. Curated Drug-Allergy Rules
ALLERGY_RULES: List[AllergyRuleDefinition] = [
    AllergyRuleDefinition(
        rule_id="ALLERGY-PEN-001",
        medication="Amoxicillin",
        allergen_class="penicillin",
        severity="HIGH",
        title="Potential Penicillin-Class Allergy Concern",
        description="Amoxicillin belongs to the penicillin class. Patient has a documented penicillin allergy.",
        evidence_source="AAAAI Drug Allergy Practice Parameter",
    ),
    AllergyRuleDefinition(
        rule_id="ALLERGY-PEN-002",
        medication="Amoxicillin-Clavulanate",
        allergen_class="penicillin",
        severity="HIGH",
        title="Potential Penicillin-Class Allergy Concern",
        description="Amoxicillin-Clavulanate contains a penicillin derivative. Patient has a documented penicillin allergy.",
        evidence_source="AAAAI Drug Allergy Practice Parameter",
    ),
    AllergyRuleDefinition(
        rule_id="ALLERGY-NSAID-001",
        medication="Aspirin",
        allergen_class="nsaid",
        severity="HIGH",
        title="Potential NSAID-Class Allergy Concern",
        description="Aspirin is a nonsteroidal anti-inflammatory agent. Patient has a documented NSAID allergy.",
        evidence_source="AAAAI Drug Allergy Practice Parameter",
    ),
    AllergyRuleDefinition(
        rule_id="ALLERGY-NSAID-002",
        medication="Ibuprofen",
        allergen_class="nsaid",
        severity="HIGH",
        title="Potential NSAID-Class Allergy Concern",
        description="Ibuprofen is an NSAID. Patient has a documented NSAID / ibuprofen allergy.",
        evidence_source="AAAAI Drug Allergy Practice Parameter",
    ),
    AllergyRuleDefinition(
        rule_id="ALLERGY-NSAID-003",
        medication="Diclofenac",
        allergen_class="nsaid",
        severity="HIGH",
        title="Potential NSAID-Class Allergy Concern",
        description="Diclofenac is an NSAID. Patient has a documented NSAID allergy.",
        evidence_source="AAAAI Drug Allergy Practice Parameter",
    ),
    AllergyRuleDefinition(
        rule_id="ALLERGY-SULFA-001",
        medication="Glimepiride",
        allergen_class="sulfa",
        severity="MODERATE",
        title="Potential Sulfonamide Cross-Reactivity Concern",
        description="Glimepiride is a sulfonylurea derivative. Patient has a documented sulfa / sulfonamide allergy.",
        evidence_source="AAAAI Drug Allergy Practice Parameter",
    ),
    AllergyRuleDefinition(
        rule_id="ALLERGY-QUIN-001",
        medication="Ciprofloxacin",
        allergen_class="quinolone",
        severity="HIGH",
        title="Potential Fluoroquinolone Allergy Concern",
        description="Ciprofloxacin is a fluoroquinolone antibiotic. Patient has a documented quinolone allergy.",
        evidence_source="AAAAI Drug Allergy Practice Parameter",
    ),
]

# 3. Curated Lab-Medication Contextual Rules
LAB_CONTEXT_RULES: List[LabContextRuleDefinition] = [
    LabContextRuleDefinition(
        rule_id="LAB-CTX-MET-CREAT-001",
        medication="Metformin",
        lab_analyte="Serum Creatinine",
        condition_status="HIGH",
        severity="HIGH",
        title="Elevated Serum Creatinine in Patient Prescribed Metformin",
        description="Recent laboratory findings show elevated serum creatinine. Renal impairment is relevant to Metformin safety review due to risk of lactic acidosis.",
        clinical_association="Renal function monitoring and clinical correlation recommended before continuing standard metformin dosing.",
        evidence_source="ADA Standards of Care / FDA Metformin Guidance",
    ),
    LabContextRuleDefinition(
        rule_id="LAB-CTX-MET-EGFR-002",
        medication="Metformin",
        lab_analyte="Estimated Glomerular Filtration Rate",
        condition_status="LOW",
        severity="HIGH",
        title="Reduced eGFR in Patient Prescribed Metformin",
        description="Recent laboratory findings indicate decreased estimated glomerular filtration rate (<60 mL/min/1.73m²).",
        clinical_association="Clinical guidelines recommend evaluating eGFR thresholds for metformin therapy.",
        evidence_source="ADA Standards of Care / KDIGO Guidelines",
    ),
    LabContextRuleDefinition(
        rule_id="LAB-CTX-ACEI-POT-003",
        medication="Ramipril",
        lab_analyte="Serum Potassium",
        condition_status="HIGH",
        severity="HIGH",
        title="Elevated Serum Potassium in Patient Prescribed ACE Inhibitor",
        description="Recent laboratory observation indicates serum potassium above reported reference range in a patient prescribed Ramipril.",
        clinical_association="Serum potassium monitoring and electrolyte correlation recommended.",
        evidence_source="KDIGO Blood Pressure Guidelines",
    ),
    LabContextRuleDefinition(
        rule_id="LAB-CTX-ARB-POT-004",
        medication="Telmisartan",
        lab_analyte="Serum Potassium",
        condition_status="HIGH",
        severity="HIGH",
        title="Elevated Serum Potassium in Patient Prescribed ARB",
        description="Recent laboratory observation indicates elevated serum potassium in a patient prescribed Telmisartan.",
        clinical_association="Serum potassium monitoring and electrolyte correlation recommended.",
        evidence_source="KDIGO Blood Pressure Guidelines",
    ),
    LabContextRuleDefinition(
        rule_id="LAB-CTX-STAT-LFT-005",
        medication="Atorvastatin",
        lab_analyte="Alanine Aminotransferase",
        condition_status="HIGH",
        severity="MODERATE",
        title="Elevated ALT Transaminase in Patient Prescribed Statin",
        description="Recent hepatic laboratory observations show elevated alanine aminotransferase (ALT) in a patient prescribed Atorvastatin.",
        clinical_association="Hepatic panel follow-up and clinical correlation recommended.",
        evidence_source="ACC/AHA Cholesterol Clinical Practice Guidelines",
    ),
    LabContextRuleDefinition(
        rule_id="LAB-CTX-STAT-AST-006",
        medication="Atorvastatin",
        lab_analyte="Aspartate Aminotransferase",
        condition_status="HIGH",
        severity="MODERATE",
        title="Elevated AST Transaminase in Patient Prescribed Statin",
        description="Recent hepatic laboratory observations show elevated aspartate aminotransferase (AST) in a patient prescribed Atorvastatin.",
        clinical_association="Hepatic panel follow-up and clinical correlation recommended.",
        evidence_source="ACC/AHA Cholesterol Clinical Practice Guidelines",
    ),
    LabContextRuleDefinition(
        rule_id="LAB-CTX-DIG-POT-007",
        medication="Digoxin",
        lab_analyte="Serum Potassium",
        condition_status="LOW",
        severity="HIGH",
        title="Low Serum Potassium in Patient Prescribed Digoxin",
        description="Hypokalemia significantly sensitizes myocardium to Digoxin toxicity even with normal digoxin concentrations.",
        clinical_association="Electrolyte replacement and electrocardiographic correlation recommended.",
        evidence_source="AHA/ACC Heart Failure Guidelines",
    ),
    LabContextRuleDefinition(
        rule_id="LAB-CTX-NSAID-CREAT-008",
        medication="Ibuprofen",
        lab_analyte="Serum Creatinine",
        condition_status="HIGH",
        severity="HIGH",
        title="Elevated Serum Creatinine in Patient Prescribed NSAID",
        description="Recent renal laboratory observations show elevated serum creatinine in a patient prescribed Ibuprofen.",
        clinical_association="Renal hemodynamic evaluation and clinical correlation recommended.",
        evidence_source="KDIGO Acute Kidney Injury Guidelines",
    ),
]

# 4. Curated Clinical Contraindication Rules
CONTRAINDICATION_RULES: List[ContraindicationRuleDefinition] = [
    ContraindicationRuleDefinition(
        rule_id="CI-NSAID-PUD-001",
        medication="Ibuprofen",
        condition="Peptic Ulcer Disease",
        severity="HIGH",
        title="NSAID Documented in Patient with Peptic Ulcer Disease History",
        description="NSAIDs inhibit prostaglandin synthesis in gastric mucosa, increasing gastrointestinal ulceration and bleeding risk.",
        evidence_source="ACG Clinical Guidelines",
    ),
    ContraindicationRuleDefinition(
        rule_id="CI-MET-CKD-002",
        medication="Metformin",
        condition="Chronic Kidney Disease Stage 4/5",
        severity="HIGH",
        title="Metformin Documented in Severe Renal Disease Context",
        description="Metformin elimination is primarily renal; severe renal disease increases potential risk of lactic acidosis.",
        evidence_source="KDIGO / ADA Guidelines",
    ),
]
