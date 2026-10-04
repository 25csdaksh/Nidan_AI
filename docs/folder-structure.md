# NIDAN AI Monorepo Folder Structure

This document outlines the directory layout for the NIDAN AI production monorepo.

```
/NIDAN_AI
├── .github/
│   └── workflows/
│       └── ci.yml                 # Automated CI/CD pipeline (backend & frontend checks)
├── backend/
│   ├── alembic/                   # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── api.py         # Root v1 router aggregator
│   │   │       └── endpoints/
│   │   │           └── health.py  # Health and readiness probes
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings management
│   │   │   ├── database.py        # SQLAlchemy async engine & session management
│   │   │   ├── errors.py          # Unified exception handling
│   │   │   ├── logging.py         # Structured JSON & console logger
│   │   │   ├── middleware.py      # Medical disclaimer, request ID & audit middlewares
│   │   │   ├── queue.py           # Background task broker abstraction
│   │   │   ├── security.py        # JWT, hashing, RBAC definitions
│   │   │   └── storage.py         # Object storage abstraction (Local/S3/MinIO)
│   │   ├── modules/               # Domain-Driven Modules
│   │   │   ├── auth/              # Authentication & Session Management
│   │   │   │   ├── models.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── users/             # Doctor / Clinician User Management
│   │   │   │   ├── models.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── patients/          # Patient Demographics & Encounters
│   │   │   │   ├── models.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── medical_records/   # Unified Medical Records & Timeline
│   │   │   │   ├── models.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── reports/           # Clinical Document Ingestion
│   │   │   │   ├── models.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── lab/               # Lab extraction & parameter tracking
│   │   │   │   ├── models.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── prescriptions/     # Prescription parsing & medication safety
│   │   │   │   ├── models.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── imaging/           # X-Ray, Sonography & DICOM metadata
│   │   │   │   ├── models.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── ai/                # Phase 0 AI contracts, interfaces & queues
│   │   │   │   ├── interfaces.py  # Abstract AI Pipeline & Extractor specs
│   │   │   │   ├── models.py      # AI analysis run models
│   │   │   │   ├── router.py      # AI job trigger & status endpoints
│   │   │   │   ├── schemas.py     # Structured clinical insight schemas
│   │   │   │   └── service.py     # Orchestration stub (no fake diagnoses)
│   │   │   ├── audit/             # HIPAA / Clinical Access Logging
│   │   │   │   ├── models.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   └── notifications/     # Clinical Alerts & Notification Service
│   │   │       ├── models.py
│   │   │       ├── router.py
│   │   │       ├── schemas.py
│   │   │       └── service.py
│   │   ├── main.py                # FastAPI application entrypoint
│   │   └── worker.py              # Background task worker entrypoint
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                       # Next.js App Router
│   │   ├── layout.tsx             # Root layout with clinical theme & disclaimer header
│   │   ├── page.tsx               # Primary clinical dashboard overview
│   │   ├── patients/              # Patient records view
│   │   ├── reports/               # Clinical document hub
│   │   └── audit/                 # Security & audit log viewer
│   ├── components/                # Reusable UI components
│   │   ├── ui/                    # Button, Card, Badge, Table, Input, etc.
│   │   ├── clinical/              # DisclaimerBanner, VitalsCard, LabTrendChart
│   │   ├── navigation/            # Header, Sidebar, UserNav
│   │   └── layout/
│   ├── lib/                       # API clients, utils, types
│   │   ├── api.ts                 # Axios / Fetch client with auth & error interceptors
│   │   ├── types.ts               # Shared TypeScript domain contracts
│   │   └── utils.ts               # Tailwind cn helper, date formatters
│   ├── public/                    # Static assets
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── Dockerfile
│   └── .env.example
├── docs/                          # Comprehensive technical documentation
│   ├── architecture.md
│   ├── folder-structure.md
│   ├── api-conventions.md
│   ├── database-strategy.md
│   ├── security-principles.md
│   └── future-ai-architecture.md
├── infra/                         # Infrastructure & orchestration
│   ├── docker-compose.yml         # Full stack local orchestration
│   ├── docker-compose.dev.yml     # Live-reload development override
│   ├── nginx/
│   │   └── nginx.conf             # Reverse proxy config
│   └── postgres/
│       └── init.sql               # Database initialization & extensions
├── tests/                         # Test suites
│   ├── backend/
│   │   ├── conftest.py            # Fixtures for async DB, mock clients
│   │   ├── test_health.py         # Health probe tests
│   │   ├── test_auth.py           # Auth & token validation tests
│   │   ├── test_patients.py       # Patient CRUD tests
│   │   ├── test_storage.py        # Storage abstraction tests
│   │   └── test_disclaimer.py     # CDSS disclaimer & guardrail tests
│   └── frontend/
│       └── smoke.test.ts          # Frontend baseline checks
├── .gitignore
└── README.md
```
