# NIDAN AI — Intelligent Clinical Insights

[![CI/CD Pipeline](https://github.com/nidan-ai/nidan-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/nidan-ai/nidan-platform/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/next.js-14+-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![License: Healthcare Standard](https://img.shields.io/badge/License-Proprietary-red.svg)]()

> ⚠️ **IMPORTANT CLINICAL & LEGAL NOTICE**  
> **NIDAN AI is NOT a doctor replacement.**  
> It must never independently provide a definitive medical diagnosis, prescription, or treatment decision.  
> It is an assistive Clinical Decision-Support System (CDSS) designed to assist qualified medical professionals by extracting information from documents, detecting abnormal laboratory values, flagging critical findings, and assembling structured longitudinal summaries.

---

## 🏥 Supported Modalities & Intelligence Engines
1. **Blood Reports & Hematology**: CBC, Lipid Panels, Liver Function Tests (LFT), Kidney Function Tests (KFT), Metabolic Panels.
2. **Clinical Intelligence & Anomaly Engine (Phase 3)**: Deterministic, demographic-aware reference range resolution (CLSI, WHO, ADA, KDIGO, AASLD), critical alerts, controlled deficiency markers, and multi-marker pattern inference (Iron deficiency, Macrocytic, Glycemic, Renal-function, Hepatic).
3. **Longitudinal Patient Intelligence & Multi-Visit Summary Engine (Phase 4)**: Normalized clinical observation repository (`clinical_observations`), prioritized observation date resolution, deterministic analyte trend engine (improving/worsening/stable trajectories with noise thresholds), abnormality dynamics detection (persistent, new, resolved, recurring, fluctuating), panel completeness checking, cross-visit comparison engine, traceable multi-visit summary synthesis, and clinician longitudinal review notes.
4. **Prescription Intelligence & Medication Safety Engine (Phase 5)**: Structured prescription extraction, controlled medication normalization, strength/route/frequency/duration parsing (strict non-inference & quantity separation), multi-engine safety screening (Drug-Drug Interactions, Documented Allergy matching, Duplicate medication detection, Lab-Medication context signals, Clinical contraindications), auditable evidence provenance, clinician verification review workflow, and longitudinal patient medication timelines.
5. **Doctor AI Copilot & Evidence-Grounded Assistant (Phase 6)**: Interactive clinical Q&A assistant grounded in verified patient observations, longitudinal trends, and medication records with deterministic evidence citations (`[EVID-...]`), prompt injection defenses, hallucination prevention, prohibited clinical decision pre-screening, and HIPAA audit logging.
6. **Medical Imaging Intelligence — Chest X-Ray Analysis & MLOps Governance (Phase 7.3)**: Assistive chest X-ray ingestion, MIME & magic bytes image validation, DICOM header extraction with strict PHI minimization, deterministic Image Quality Gate (`QUALITY_ACCEPTED`, `QUALITY_WARNING`, `QUALITY_REJECTED`), versioned preprocessing (`xray-preprocess-v1`), pluggable vision model registry (`ChestXRayDeterministicTestModel` marked DEMO/TEST ONLY, `NativeVisionChestModel` marked EXPERIMENTAL HEURISTIC, deep learning PyTorch/ONNX adapters with checksum integrity), controlled 12-label taxonomy, temperature scaling calibration, uncertainty margins, Grad-CAM/attention explainability localization, evidence provenance (`EVID-XRAY-...`), MLOps dataset validation (`scripts/validate_xray_dataset.py`), reproducible training pipeline (`scripts/train_xray_model.py`), four-tier clinical evaluation suite (`scripts/evaluate_xray_model.py`), clinician review workflow (`PENDING`, `ACCEPTED`, `MODIFIED`, `REJECTED`) with immutable model records, longitudinal imaging timeline, and Doctor Copilot integration.
7. **Sonography / Ultrasound**: USG scans, biometric measurement extraction, structured impression logs (Roadmap).



---

## 🏛️ Monorepo Architecture

```
/NIDAN_AI
├── backend/            # FastAPI Async Backend (Python 3.10+)
│   ├── app/
│   │   ├── api/v1/     # Versioned REST endpoints (/api/v1)
│   │   ├── core/       # Security, DB, Logging, Storage & Queue Broker
│   │   └── modules/    # 11 Modular Domain Services (Auth, Patients, Lab, AI...)
│   └── alembic/        # Async Database Migrations
├── frontend/           # Next.js 14 App Router (TypeScript, Tailwind, shadcn-inspired UI)
│   ├── app/            # Clinical dashboard, patient registry, reports hub, audit trail
│   ├── components/     # Accessible clinical UI components & CDSS banner
│   └── lib/            # Typed API clients & domain models
├── infra/              # Docker Compose (PostgreSQL 15, Redis 7, Nginx reverse proxy)
├── docs/               # System Architecture, Database Strategy, Security, AI Roadmaps
└── tests/              # Pytest async test suite (Health, Auth, Patients, Reports, Lab)
```

---

## 🚀 Quickstart Guide

### Option 1: Full Stack via Docker Compose (Recommended)
```bash
# Start all services (PostgreSQL, Redis, Backend API, Worker, Next.js, Nginx)
docker-compose -f infra/docker-compose.yml up --build
```
- **Web Portal**: `http://localhost:3000` (or `http://localhost`)
- **API Health Probe**: `http://localhost:8000/api/v1/health`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

---

### Option 2: Local Development Setup

#### 1. Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Running Automated Tests

```bash
# Run backend pytest suite
pytest tests/backend -v
```

---

## 🔒 Security & Healthcare Compliance Principles
- **HIPAA Compliant Audit Trail**: Immutable logging of every patient data access and modification.
- **Human-in-the-Loop (HITL)**: Mandatory doctor review and sign-off on AI-suggested findings.
- **Storage Encryption**: AES-256 encrypted local or S3 object store for raw medical scans.
- **CDSS Disclaimer Headers**: Automatically injected on every HTTP response via middleware.

---

## 📖 Detailed Technical Documentation
- [Phase 7.6 Implementation Report](docs/PHASE_7_6_IMPLEMENTATION_REPORT.md)
- [Phase 7.6 Held-Out Dataset Evaluation & Audit](docs/phase7.6-heldout-dataset-evaluation.md)
- [Phase 7.5 Implementation Report](docs/PHASE_7_5_IMPLEMENTATION_REPORT.md)
- [Phase 7.5 Pretrained Model Verification Report](docs/phase7.5-pretrained-model-verification.md)
- [Medical Imaging Intelligence (Phase 7)](docs/imaging-intelligence.md)
- [Phase 7.4 Implementation Report](docs/PHASE_7_4_IMPLEMENTATION_REPORT.md)
- [Phase 7.4 Dataset & Model Selection Report](docs/phase7.4-dataset-and-model-selection.md)
- [Phase 7.3 Implementation Report](docs/PHASE_7_3_IMPLEMENTATION_REPORT.md)
- [Phase 7.3 Model & Dataset Readiness Report](docs/phase7.3-model-and-dataset-readiness.md)
- [Chest X-Ray Model Architecture](docs/xray-model-architecture.md)
- [Imaging Dataset Governance](docs/xray-dataset-governance.md)
- [Imaging Security & DICOM Privacy](docs/imaging-security.md)
- [Imaging Clinical Safety & CDSS Boundaries](docs/imaging-clinical-safety.md)
- [Imaging API Specifications](docs/imaging-api.md)
- [Doctor AI Copilot (Phase 6)](docs/doctor-copilot.md)
- [Prescription Intelligence (Phase 5)](docs/prescription-intelligence.md)
- [Longitudinal Patient Intelligence (Phase 4)](docs/longitudinal-intelligence.md)
- [OCR & Medical Document Extraction (Phase 2)](docs/ocr-extraction.md)
- [Medical Document Ingestion (Phase 1)](docs/medical-document-ingestion.md)
- [System Architecture](docs/architecture.md)
- [Folder Structure](docs/folder-structure.md)
- [API Conventions](docs/api-conventions.md)
- [Database Strategy](docs/database-strategy.md)
- [Security Principles](docs/security-principles.md)
- [Future AI Pipeline Architecture](docs/future-ai-architecture.md)


