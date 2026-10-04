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
4. **Prescriptions (Rx)**: Medication names, dosage regimens, frequencies, routes, duration, and safety interaction tracking.
5. **Chest & Skeletal X-Rays**: DICOM metadata, radiograph study linking, radiologist impression extraction.
6. **Sonography / Ultrasound**: USG scans, biometric measurement extraction, structured impression logs.


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
- [OCR & Medical Document Extraction (Phase 2)](docs/ocr-extraction.md)
- [Medical Document Ingestion (Phase 1)](docs/medical-document-ingestion.md)
- [System Architecture](docs/architecture.md)
- [Folder Structure](docs/folder-structure.md)
- [API Conventions](docs/api-conventions.md)
- [Database Strategy](docs/database-strategy.md)
- [Security Principles](docs/security-principles.md)
- [Future AI Pipeline Architecture](docs/future-ai-architecture.md)


