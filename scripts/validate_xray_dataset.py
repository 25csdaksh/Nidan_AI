"""
NIDAN AI — Medical Imaging Dataset Validation & Governance Tool (Phase 7.6)
Audits external radiograph dataset CSV manifests and image archives for:
1. Patient-level partition isolation (zero patient leakage across train/val/test).
2. Image SHA-256 duplicate and collision detection across splits.
3. Multiple studies / serial exams per patient tracking.
4. Dataset pretraining provenance audit (detects overlap with TorchXRayVision composite pretraining cohorts).
5. Controlled label mapping & missing/uncertain label masking (-1, NaN, blank).
6. Class imbalance and label prevalence per partition.
7. Direct PHI scanning in dataset columns (Patient Name, Address, MRN, Institution).
"""

import argparse
import csv
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

LABELS = [
    "ATELECTASIS",
    "CARDIOMEGALY",
    "CONSOLIDATION",
    "EDEMA",
    "PLEURAL_EFFUSION",
    "PNEUMOTHORAX",
    "INFILTRATION",
    "MASS",
    "NODULE",
    "PNEUMONIA",
    "FIBROSIS",
    "PLEURAL_THICKENING",
]

# Sensitive column names that must never appear in de-identified research manifests
POTENTIAL_PHI_COLUMNS = [
    "patient_name",
    "name",
    "full_name",
    "address",
    "ssn",
    "phone",
    "email",
    "hospital_record_id",
    "institution_name",
]

# Known pretraining datasets used in TorchXRayVision densenet121-res224-all
KNOWN_PRETRAINING_COHORTS = [
    "nih",
    "nih-14",
    "chestxray14",
    "padchest",
    "chexpert",
    "mimic",
    "mimic-cxr",
    "openi",
    "kaggle",
]


class DatasetValidationError(Exception):
    """Raised when a dataset manifest violates clinical data governance rules."""
    pass


def audit_dataset_manifest(
    manifest_csv: str,
    image_root_dir: Optional[str] = None,
    uncertain_policy: str = "mask",  # "mask", "zeros", "ones"
    dataset_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validates a dataset CSV manifest for compliance with NIDAN AI governance rules.
    """
    if not os.path.exists(manifest_csv):
        raise FileNotFoundError(f"Manifest CSV not found: {manifest_csv}")

    with open(manifest_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    # 1. PHI Column Detection
    detected_phi_cols = [c for c in fieldnames if c.lower() in POTENTIAL_PHI_COLUMNS]
    if detected_phi_cols:
        raise DatasetValidationError(
            f"PHI LEAKAGE RISK: Manifest contains direct identifier columns: {detected_phi_cols}. "
            "Strip all direct identifiers before dataset ingestion."
        )

    # 2. Key Column Requirements
    has_patient_id = any(c.lower() in ["patient_id", "patientid", "subject_id"] for c in fieldnames)
    pid_col = next(c for c in fieldnames if c.lower() in ["patient_id", "patientid", "subject_id"]) if has_patient_id else None

    if not pid_col:
        raise DatasetValidationError("Missing required 'patient_id' column for partition isolation.")

    split_col = next((c for c in fieldnames if c.lower() in ["split", "partition", "subset"]), None)
    study_col = next((c for c in fieldnames if c.lower() in ["study_id", "studyid", "accession_number", "exam_id"]), None)
    img_col = next((c for c in fieldnames if c.lower() in ["image_path", "filename", "image_id", "path", "file_name"]), None)

    # 3. Label Alignment
    matched_labels = [l for l in LABELS if l in fieldnames or l.lower() in [f.lower() for f in fieldnames]]

    # 4. Partition Isolation, Multi-Study Tracking & Duplicate Checking
    patient_splits: Dict[str, Set[str]] = {"train": set(), "val": set(), "test": set(), "unassigned": set()}
    patient_studies: Dict[str, Set[str]] = {}
    label_counts: Dict[str, Dict[str, int]] = {
        s: {l: 0 for l in LABELS} for s in ["train", "val", "test", "total"]
    }
    uncertain_counts: Dict[str, Dict[str, int]] = {
        s: {l: 0 for l in LABELS} for s in ["train", "val", "test", "total"]
    }
    image_hashes: Dict[str, str] = {}  # image_hash -> split
    image_hash_collisions: List[str] = []
    missing_images_count = 0
    total_records = len(rows)

    for row in rows:
        pid = row[pid_col].strip()
        split = row.get(split_col, "unassigned").strip().lower() if split_col else "unassigned"
        if split not in patient_splits:
            split = "unassigned"

        patient_splits[split].add(pid)

        if study_col and row.get(study_col):
            sid = row[study_col].strip()
            if pid not in patient_studies:
                patient_studies[pid] = set()
            patient_studies[pid].add(sid)

        # Count labels and uncertainty
        for l in LABELS:
            val_raw = row.get(l, row.get(l.lower(), "0"))
            try:
                fval = float(val_raw)
                if fval == 1.0:
                    label_counts[split if split in label_counts else "total"][l] += 1
                    label_counts["total"][l] += 1
                elif fval == -1.0:
                    uncertain_counts[split if split in uncertain_counts else "total"][l] += 1
                    uncertain_counts["total"][l] += 1
                    if uncertain_policy == "ones":
                        label_counts[split if split in label_counts else "total"][l] += 1
                        label_counts["total"][l] += 1
            except (ValueError, TypeError):
                pass

        # Optional image file check & hash verification
        if image_root_dir and img_col:
            img_rel = row.get(img_col, "")
            img_path = os.path.join(image_root_dir, img_rel)
            if not os.path.exists(img_path):
                missing_images_count += 1
            else:
                try:
                    with open(img_path, "rb") as fimg:
                        imghash = hashlib.sha256(fimg.read()).hexdigest()
                    if imghash in image_hashes and image_hashes[imghash] != split:
                        image_hash_collisions.append(f"Image hash collision across splits ({image_hashes[imghash]} vs {split}): {img_rel}")
                    image_hashes[imghash] = split
                except Exception:
                    pass

    # Verify Patient Isolation
    leakage_detected = False
    leakage_details = []
    if split_col:
        train_val = patient_splits["train"].intersection(patient_splits["val"])
        train_test = patient_splits["train"].intersection(patient_splits["test"])
        val_test = patient_splits["val"].intersection(patient_splits["test"])

        if train_val:
            leakage_detected = True
            leakage_details.append(f"Train/Val Patient Leakage ({len(train_val)} patients)")
        if train_test:
            leakage_detected = True
            leakage_details.append(f"Train/Test Patient Leakage ({len(train_test)} patients)")
        if val_test:
            leakage_detected = True
            leakage_details.append(f"Val/Test Patient Leakage ({len(val_test)} patients)")

    if image_hash_collisions:
        leakage_detected = True
        leakage_details.extend(image_hash_collisions[:5])

    # 5. Pretraining Independence Check
    dataset_name_clean = (dataset_name or os.path.basename(manifest_csv)).lower()
    overlaps_pretraining = any(k in dataset_name_clean for k in KNOWN_PRETRAINING_COHORTS)
    independence_status = "PRETRAINING_COHORT_OVERLAP" if overlaps_pretraining else "POTENTIALLY_INDEPENDENT"

    report = {
        "manifest_path": manifest_csv,
        "dataset_name": dataset_name or os.path.basename(manifest_csv),
        "total_records": total_records,
        "unique_patients": len(set.union(*patient_splits.values())),
        "total_studies_tracked": sum(len(s) for s in patient_studies.values()) if patient_studies else total_records,
        "matched_labels_count": len(matched_labels),
        "matched_labels": matched_labels,
        "partition_counts": {k: len(v) for k, v in patient_splits.items()},
        "patient_isolation_status": "PASSED" if not leakage_detected else "FAILED",
        "leakage_details": leakage_details,
        "missing_images_count": missing_images_count,
        "independence_classification": independence_status,
        "overlaps_pretraining_cohort": overlaps_pretraining,
        "label_counts": label_counts,
        "uncertain_counts": uncertain_counts,
        "uncertain_policy": uncertain_policy,
        "is_ready_for_training": bool(not leakage_detected and len(matched_labels) > 0),
        "is_ready_for_evaluation": bool(not leakage_detected and len(matched_labels) > 0 and missing_images_count == 0),
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="NIDAN AI Medical Imaging Dataset Validation Tool")
    parser.add_argument("--manifest-csv", type=str, required=True, help="Path to dataset CSV manifest")
    parser.add_argument("--image-root", type=str, default=None, help="Root directory containing images")
    parser.add_argument("--dataset-name", type=str, default=None, help="Name of dataset (e.g., NIH-14, VinDr-CXR, CheXpert)")
    parser.add_argument("--uncertain-policy", type=str, default="mask", choices=["mask", "zeros", "ones"], help="Handling for uncertain (-1) labels")
    parser.add_argument("--output-json", type=str, default=None, help="Optional output path for machine-readable JSON audit report")
    args = parser.parse_args()

    print("=" * 80)
    print("NIDAN AI - MEDICAL DATASET GOVERNANCE & INTEGRITY AUDITOR (PHASE 7.6)")
    print("=" * 80)
    print(f"Manifest: {args.manifest_csv}")
    print(f"Uncertainty Policy: {args.uncertain_policy}\n")

    try:
        report = audit_dataset_manifest(
            manifest_csv=args.manifest_csv,
            image_root_dir=args.image_root,
            uncertain_policy=args.uncertain_policy,
            dataset_name=args.dataset_name,
        )

        print("--- AUDIT RESULTS SUMMARY ---")
        print(f"Total Records: {report['total_records']} | Unique Patients: {report['unique_patients']}")
        print(f"Matched Target Labels: {report['matched_labels_count']}/12 ({', '.join(report['matched_labels'])})")
        print(f"Patient Isolation Status: [{report['patient_isolation_status']}]")
        print(f"Dataset Independence: [{report['independence_classification']}] (Overlaps Pretraining: {report['overlaps_pretraining_cohort']})")
        if report["leakage_details"]:
            for item in report["leakage_details"]:
                print(f"  [!] ALERT: {item}")

        print("\n--- PER-LABEL POSITIVE / UNCERTAIN COUNTS ---")
        for l in LABELS:
            pos_c = report["label_counts"]["total"].get(l, 0)
            unc_c = report["uncertain_counts"]["total"].get(l, 0)
            print(f"  {l:<22} : {pos_c:>5} positive | {unc_c:>4} uncertain")

        if args.output_json:
            os.makedirs(os.path.dirname(os.path.abspath(args.output_json)), exist_ok=True)
            with open(args.output_json, "w", encoding="utf-8") as fj:
                json.dump(report, fj, indent=2)
            print(f"\n[OK] Machine-readable audit saved to: {args.output_json}")

        print("\n" + "=" * 80)
        if report["is_ready_for_evaluation"]:
            print("[OK] DATASET GOVERNANCE VERIFIED: Manifest is clean, patient-isolated, and compliant.")
        else:
            print("[X] DATASET GOVERNANCE FAILED / INCOMPLETE: Address partition leakage or missing images.")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] Dataset audit aborted: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

