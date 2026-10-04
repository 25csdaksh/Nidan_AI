"""Controlled Medication Vocabulary and Catalogs for NIDAN AI Phase 5.

Provides deterministic dictionaries and mappings for:
- Medications (generic, canonical, brand names, aliases, drug classes)
- Dosage forms (tablet, capsule, syrup, injection, drops, inhaler, etc.)
- Strength units (mg, g, mcg, ml, IU, %, meq, meq/l)
- Administration routes (oral, PO, IV, IM, SC, topical, ophthalmic, otic, inhaled, sublingual, rectal)
- Frequency abbreviations & descriptions (OD, BD, TID, QID, Q8H, PRN, etc.)
- Duration units (days, weeks, months, years)
- Drug classes & allergen mappings
"""

from typing import Dict, List, Optional, Set, Tuple

# 1. Standard Route Catalog
ROUTES_MAP: Dict[str, str] = {
    "po": "ORAL",
    "oral": "ORAL",
    "by mouth": "ORAL",
    "p.o.": "ORAL",
    "iv": "INTRAVENOUS",
    "i.v.": "INTRAVENOUS",
    "intravenous": "INTRAVENOUS",
    "im": "INTRAMUSCULAR",
    "i.m.": "INTRAMUSCULAR",
    "intramuscular": "INTRAMUSCULAR",
    "sc": "SUBCUTANEOUS",
    "s.c.": "SUBCUTANEOUS",
    "subcut": "SUBCUTANEOUS",
    "subcutaneous": "SUBCUTANEOUS",
    "topical": "TOPICAL",
    "local application": "TOPICAL",
    "ophthalmic": "OPHTHALMIC",
    "eye drops": "OPHTHALMIC",
    "otic": "OTIC",
    "ear drops": "OTIC",
    "inhaled": "INHALED",
    "inhalation": "INHALED",
    "sublingual": "SUBLINGUAL",
    "s.l.": "SUBLINGUAL",
    "rectal": "RECTAL",
    "p.r.": "RECTAL",
    "nasal": "NASAL",
    "nasal spray": "NASAL",
}

# 2. Standard Dosage Forms
DOSAGE_FORMS: Set[str] = {
    "tablet", "tab", "tabs", "tab.",
    "capsule", "cap", "caps", "cap.",
    "syrup", "syp", "syp.",
    "suspension", "susp", "susp.",
    "injection", "inj", "inj.",
    "solution", "soln",
    "ointment", "oint", "oint.",
    "cream", "crm",
    "gel",
    "drops", "drop",
    "inhaler", "puff", "puffs",
    "patch", "transdermal patch",
    "lotion",
    "suppository", "supp",
    "powder", "sachet",
}

DOSAGE_FORM_CANONICAL: Dict[str, str] = {
    "tab": "Tablet", "tabs": "Tablet", "tab.": "Tablet", "tablet": "Tablet",
    "cap": "Capsule", "caps": "Capsule", "cap.": "Capsule", "capsule": "Capsule",
    "syp": "Syrup", "syp.": "Syrup", "syrup": "Syrup",
    "susp": "Suspension", "susp.": "Suspension", "suspension": "Suspension",
    "inj": "Injection", "inj.": "Injection", "injection": "Injection",
    "soln": "Solution", "solution": "Solution",
    "oint": "Ointment", "oint.": "Ointment", "ointment": "Ointment",
    "crm": "Cream", "cream": "Cream",
    "gel": "Gel",
    "drops": "Drops", "drop": "Drops",
    "inhaler": "Inhaler", "puff": "Inhaler", "puffs": "Inhaler",
    "patch": "Patch",
    "lotion": "Lotion",
    "supp": "Suppository", "suppository": "Suppository",
    "sachet": "Powder/Sachet", "powder": "Powder/Sachet",
}

# 3. Standard Strength Units
STRENGTH_UNITS: Set[str] = {
    "mg", "g", "gram", "grams", "mcg", "ug", "microgram", "micrograms",
    "ml", "l", "iu", "units", "u", "%", "meq", "meq/l", "mg/ml", "mg/5ml",
}

# 4. Standard Frequency Expressions & Normalization
FREQUENCY_MAP: Dict[str, Tuple[str, str]] = {
    # Abbreviation: (Code, Standard Description)
    "od": ("OD", "once daily"),
    "once daily": ("OD", "once daily"),
    "once a day": ("OD", "once daily"),
    "qd": ("OD", "once daily"),
    "q.d.": ("OD", "once daily"),
    "daily": ("OD", "once daily"),
    "every morning": ("QAM", "every morning"),
    "qam": ("QAM", "every morning"),
    "every evening": ("QPM", "every evening"),
    "qpm": ("QPM", "every evening"),
    "at bedtime": ("QHS", "at bedtime"),
    "qhs": ("QHS", "at bedtime"),
    "hs": ("QHS", "at bedtime"),

    "bd": ("BID", "twice daily"),
    "bid": ("BID", "twice daily"),
    "b.i.d.": ("BID", "twice daily"),
    "twice daily": ("BID", "twice daily"),
    "twice a day": ("BID", "twice daily"),
    "every 12 hours": ("Q12H", "every 12 hours"),
    "q12h": ("Q12H", "every 12 hours"),

    "tds": ("TID", "three times daily"),
    "tid": ("TID", "three times daily"),
    "t.i.d.": ("TID", "three times daily"),
    "three times daily": ("TID", "three times daily"),
    "thrice daily": ("TID", "three times daily"),
    "thrice a day": ("TID", "three times daily"),
    "every 8 hours": ("Q8H", "every 8 hours"),
    "q8h": ("Q8H", "every 8 hours"),

    "qid": ("QID", "four times daily"),
    "q.i.d.": ("QID", "four times daily"),
    "four times daily": ("QID", "four times daily"),
    "4 times daily": ("QID", "four times daily"),
    "every 6 hours": ("Q6H", "every 6 hours"),
    "q6h": ("Q6H", "every 6 hours"),

    "prn": ("PRN", "as needed"),
    "p.r.n.": ("PRN", "as needed"),
    "as needed": ("PRN", "as needed"),
    "sos": ("SOS", "as needed in emergency"),
    "when required": ("PRN", "as needed"),

    "stat": ("STAT", "immediately"),
    "weekly": ("QW", "once weekly"),
    "once weekly": ("QW", "once weekly"),
    "once a week": ("QW", "once weekly"),
    "every other day": ("QOD", "every other day"),
    "qod": ("QOD", "every other day"),
}

# 5. Timing / Meal Instructions
MEAL_INSTRUCTIONS_MAP: Dict[str, str] = {
    "ac": "before meals",
    "a.c.": "before meals",
    "before meals": "before meals",
    "before food": "before meals",
    "empty stomach": "on an empty stomach",
    "pc": "after meals",
    "p.c.": "after meals",
    "after meals": "after meals",
    "after food": "after meals",
    "with meals": "with meals",
    "with food": "with meals",
}

# 6. Authoritative Medication Catalog
# canonical_name -> { "generic": str, "aliases": set, "classes": list, "brand_names": set }
MEDICATION_CATALOG: Dict[str, dict] = {
    "Metformin": {
        "generic": "Metformin Hydrochloride",
        "aliases": {"metformin", "metformin hcl", "metformin hydrochloride", "glycomet", "glucophage", "obimet", "riomet"},
        "classes": ["Biguanide", "Antidiabetic"],
        "brand_names": {"Glycomet", "Glucophage", "Obimet", "Riomet"},
    },
    "Atorvastatin": {
        "generic": "Atorvastatin Calcium",
        "aliases": {"atorvastatin", "atorvastatin calcium", "lipitor", "atorva", "atorlip", "storvas"},
        "classes": ["HMG-CoA Reductase Inhibitor", "Statin", "Lipid-Lowering Agent"],
        "brand_names": {"Lipitor", "Atorva", "Atorlip", "Storvas"},
    },
    "Rosuvastatin": {
        "generic": "Rosuvastatin Calcium",
        "aliases": {"rosuvastatin", "rosuvastatin calcium", "crestor", "rosuvas", "razel", "rosavel"},
        "classes": ["HMG-CoA Reductase Inhibitor", "Statin", "Lipid-Lowering Agent"],
        "brand_names": {"Crestor", "Rosuvas", "Razel", "Rosavel"},
    },
    "Amlodipine": {
        "generic": "Amlodipine Besylate",
        "aliases": {"amlodipine", "amlodipine besylate", "norvasc", "amlong", "stamlo", "amlovas"},
        "classes": ["Calcium Channel Blocker", "Dihydropyridine", "Antihypertensive"],
        "brand_names": {"Norvasc", "Amlong", "Stamlo", "Amlovas"},
    },
    "Telmisartan": {
        "generic": "Telmisartan",
        "aliases": {"telmisartan", "micardis", "telma", "telpres", "telsartan"},
        "classes": ["Angiotensin Receptor Blocker", "ARB", "Antihypertensive"],
        "brand_names": {"Micardis", "Telma", "Telpres", "Telsartan"},
    },
    "Losartan": {
        "generic": "Losartan Potassium",
        "aliases": {"losartan", "losartan potassium", "cozaar", "losacar", "repace", "tozaar"},
        "classes": ["Angiotensin Receptor Blocker", "ARB", "Antihypertensive"],
        "brand_names": {"Cozaar", "Losacar", "Repace", "Tozaar"},
    },
    "Ramipril": {
        "generic": "Ramipril",
        "aliases": {"ramipril", "altace", "cardace", "hopace", "ramace"},
        "classes": ["ACE Inhibitor", "Antihypertensive"],
        "brand_names": {"Altace", "Cardace", "Hopace", "Ramace"},
    },
    "Enalapril": {
        "generic": "Enalapril Maleate",
        "aliases": {"enalapril", "enalapril maleate", "vasotec", "envas", "nuril"},
        "classes": ["ACE Inhibitor", "Antihypertensive"],
        "brand_names": {"Vasotec", "Envas", "Nuril"},
    },
    "Lisinopril": {
        "generic": "Lisinopril",
        "aliases": {"lisinopril", "prinivil", "zestril", "listril", "lipril"},
        "classes": ["ACE Inhibitor", "Antihypertensive"],
        "brand_names": {"Prinivil", "Zestril", "Listril", "Lipril"},
    },
    "Aspirin": {
        "generic": "Acetylsalicylic Acid",
        "aliases": {"aspirin", "acetylsalicylic acid", "ecosprin", "disprin", "bayer aspirin", "asa"},
        "classes": ["Antiplatelet", "NSAID", "Salicylate"],
        "brand_names": {"Ecosprin", "Disprin", "Bayer Aspirin"},
    },
    "Clopidogrel": {
        "generic": "Clopidogrel Bisulfate",
        "aliases": {"clopidogrel", "clopidogrel bisulfate", "plavix", "clopilet", "ceruvin", "deplatt"},
        "classes": ["Antiplatelet", "P2Y12 Inhibitor"],
        "brand_names": {"Plavix", "Clopilet", "Ceruvin", "Deplatt"},
    },
    "Warfarin": {
        "generic": "Warfarin Sodium",
        "aliases": {"warfarin", "warfarin sodium", "coumadin", "warfone", "uniwarfin"},
        "classes": ["Anticoagulant", "Vitamin K Antagonist"],
        "brand_names": {"Coumadin", "Warfone", "Uniwarfin"},
    },
    "Apixaban": {
        "generic": "Apixaban",
        "aliases": {"apixaban", "eliquis", "apigat"},
        "classes": ["Anticoagulant", "DOAC", "Factor Xa Inhibitor"],
        "brand_names": {"Eliquis", "Apigat"},
    },
    "Rivaroxaban": {
        "generic": "Rivaroxaban",
        "aliases": {"rivaroxaban", "xarelto", "ixaro"},
        "classes": ["Anticoagulant", "DOAC", "Factor Xa Inhibitor"],
        "brand_names": {"Xarelto", "Ixaro"},
    },
    "Omeprazole": {
        "generic": "Omeprazole",
        "aliases": {"omeprazole", "prilosec", "omez", "ocid", "omizac"},
        "classes": ["Proton Pump Inhibitor", "PPI", "Antiulcer"],
        "brand_names": {"Prilosec", "Omez", "Ocid", "Omizac"},
    },
    "Pantoprazole": {
        "generic": "Pantoprazole Sodium",
        "aliases": {"pantoprazole", "pantoprazole sodium", "protonix", "pantocid", "pan 40", "pantodac"},
        "classes": ["Proton Pump Inhibitor", "PPI", "Antiulcer"],
        "brand_names": {"Protonix", "Pantocid", "Pan 40", "Pantodac"},
    },
    "Ibuprofen": {
        "generic": "Ibuprofen",
        "aliases": {"ibuprofen", "advil", "motrin", "brufen", "ibugesic"},
        "classes": ["NSAID", "Analgesic", "Antipyretic"],
        "brand_names": {"Advil", "Motrin", "Brufen", "Ibugesic"},
    },
    "Diclofenac": {
        "generic": "Diclofenac Sodium",
        "aliases": {"diclofenac", "diclofenac sodium", "diclofenac potassium", "voltaren", "voveran", "dynapar"},
        "classes": ["NSAID", "Analgesic"],
        "brand_names": {"Voltaren", "Voveran", "Dynapar"},
    },
    "Paracetamol": {
        "generic": "Acetaminophen",
        "aliases": {"paracetamol", "acetaminophen", "tylenol", "crocin", "calpol", "dolo 650", "dolo", "panadol"},
        "classes": ["Analgesic", "Antipyretic"],
        "brand_names": {"Tylenol", "Crocin", "Calpol", "Dolo 650", "Panadol"},
    },
    "Amoxicillin": {
        "generic": "Amoxicillin Trihydrate",
        "aliases": {"amoxicillin", "amoxicillin trihydrate", "amoxil", "novamox", "mox"},
        "classes": ["Penicillin Antibiotic", "Beta-Lactam", "Antibacterial"],
        "brand_names": {"Amoxil", "Novamox", "Mox"},
    },
    "Amoxicillin-Clavulanate": {
        "generic": "Amoxicillin and Clavulanate Potassium",
        "aliases": {"amoxicillin-clavulanate", "amoxicillin and clavulanate", "augmentin", "moxikind-cv", "clamoxyl", "clavulin"},
        "classes": ["Penicillin Antibiotic", "Beta-Lactam / Beta-Lactamase Inhibitor"],
        "brand_names": {"Augmentin", "Moxikind-CV", "Clamoxyl", "Clavulin"},
    },
    "Azithromycin": {
        "generic": "Azithromycin",
        "aliases": {"azithromycin", "zithromax", "azee", "aziwok", "azithral"},
        "classes": ["Macrolide Antibiotic", "Antibacterial"],
        "brand_names": {"Zithromax", "Azee", "Aziwok", "Azithral"},
    },
    "Ciprofloxacin": {
        "generic": "Ciprofloxacin Hydrochloride",
        "aliases": {"ciprofloxacin", "cipro", "ciplox", "cifran"},
        "classes": ["Fluoroquinolone Antibiotic", "Antibacterial"],
        "brand_names": {"Cipro", "Ciplox", "Cifran"},
    },
    "Levofloxacin": {
        "generic": "Levofloxacin",
        "aliases": {"levofloxacin", "levaquin", "levomac", "glevo"},
        "classes": ["Fluoroquinolone Antibiotic", "Antibacterial"],
        "brand_names": {"Levaquin", "Levomac", "Glevo"},
    },
    "Doxycycline": {
        "generic": "Doxycycline Hyclate",
        "aliases": {"doxycycline", "doxycycline hyclate", "doryx", "doxicip", "doxylin"},
        "classes": ["Tetracycline Antibiotic", "Antibacterial"],
        "brand_names": {"Doryx", "Doxicip", "Doxylin"},
    },
    "Spironolactone": {
        "generic": "Spironolactone",
        "aliases": {"spironolactone", "aldactone", "aldacton"},
        "classes": ["Potassium-Sparing Diuretic", "Aldosterone Antagonist"],
        "brand_names": {"Aldactone"},
    },
    "Furosemide": {
        "generic": "Furosemide",
        "aliases": {"furosemide", "lasix", "frusene"},
        "classes": ["Loop Diuretic", "Antihypertensive"],
        "brand_names": {"Lasix"},
    },
    "Hydrochlorothiazide": {
        "generic": "Hydrochlorothiazide",
        "aliases": {"hydrochlorothiazide", "hctz", "microzide", "aquazide"},
        "classes": ["Thiazide Diuretic", "Antihypertensive"],
        "brand_names": {"Microzide", "Aquazide"},
    },
    "Glimepiride": {
        "generic": "Glimepiride",
        "aliases": {"glimepiride", "amaryl", "galyx", "zoryl"},
        "classes": ["Sulfonylurea", "Antidiabetic"],
        "brand_names": {"Amaryl", "Galyx", "Zoryl"},
    },
    "Sitagliptin": {
        "generic": "Sitagliptin Phosphate",
        "aliases": {"sitagliptin", "januvia", "istavel", "janumet"},
        "classes": ["DPP-4 Inhibitor", "Antidiabetic"],
        "brand_names": {"Januvia", "Istavel"},
    },
    "Empagliflozin": {
        "generic": "Empagliflozin",
        "aliases": {"empagliflozin", "jardiance", "gibb-emp"},
        "classes": ["SGLT2 Inhibitor", "Antidiabetic"],
        "brand_names": {"Jardiance"},
    },
    "Dapagliflozin": {
        "generic": "Dapagliflozin",
        "aliases": {"dapagliflozin", "farxiga", "forxiga", "oxra"},
        "classes": ["SGLT2 Inhibitor", "Antidiabetic"],
        "brand_names": {"Farxiga", "Forxiga", "Oxra"},
    },
    "Insulin Glargine": {
        "generic": "Insulin Glargine",
        "aliases": {"insulin glargine", "lantus", "toujeo", "basaglar"},
        "classes": ["Long-Acting Insulin", "Antidiabetic"],
        "brand_names": {"Lantus", "Toujeo", "Basaglar"},
    },
    "Levothyroxine": {
        "generic": "Levothyroxine Sodium",
        "aliases": {"levothyroxine", "levothyroxine sodium", "synthroid", "eltroxin", "thyronorm"},
        "classes": ["Thyroid Hormone", "Endocrine"],
        "brand_names": {"Synthroid", "Eltroxin", "Thyronorm"},
    },
    "Methotrexate": {
        "generic": "Methotrexate Sodium",
        "aliases": {"methotrexate", "trexall", "folitrax", "mexate"},
        "classes": ["Antimetabolite", "DMARD", "Immunosuppressant"],
        "brand_names": {"Trexall", "Folitrax", "Mexate"},
    },
    "Digoxin": {
        "generic": "Digoxin",
        "aliases": {"digoxin", "lanoxin", "digolan"},
        "classes": ["Cardiac Glycoside", "Antiarrhythmic", "Inotrope"],
        "brand_names": {"Lanoxin", "Digolan"},
    },
    "Amiodarone": {
        "generic": "Amiodarone Hydrochloride",
        "aliases": {"amiodarone", "cordarone", "pacerone"},
        "classes": ["Class III Antiarrhythmic"],
        "brand_names": {"Cordarone", "Pacerone"},
    },
    "Allopurinol": {
        "generic": "Allopurinol",
        "aliases": {"allopurinol", "zyloprim", "zyloric"},
        "classes": ["Xanthine Oxidase Inhibitor", "Antigout"],
        "brand_names": {"Zyloprim", "Zyloric"},
    },
    "Cetirizine": {
        "generic": "Cetirizine Hydrochloride",
        "aliases": {"cetirizine", "zyrtec", "cetzine", "alerid"},
        "classes": ["Antihistamine", "H1 Blocker"],
        "brand_names": {"Zyrtec", "Cetzine", "Alerid"},
    },
}

# 7. Allergen Class Mappings
# Drug -> Allergen Classes
DRUG_TO_ALLERGEN_CLASSES: Dict[str, List[str]] = {
    "Amoxicillin": ["penicillin", "beta-lactam", "antibiotics"],
    "Amoxicillin-Clavulanate": ["penicillin", "beta-lactam", "antibiotics"],
    "Aspirin": ["nsaid", "aspirin", "salicylate"],
    "Ibuprofen": ["nsaid", "ibuprofen"],
    "Diclofenac": ["nsaid", "diclofenac"],
    "Ciprofloxacin": ["quinolone", "fluoroquinolone", "ciprofloxacin"],
    "Levofloxacin": ["quinolone", "fluoroquinolone", "levofloxacin"],
    "Doxycycline": ["tetracycline", "doxycycline"],
    "Glimepiride": ["sulfa", "sulfonamide", "sulfonylurea"],
    "Hydrochlorothiazide": ["sulfa", "sulfonamide", "thiazide"],
}
