# AI Clinical Document Reviewer

An intelligent, multi-modal clinical document review, entity extraction, and safety verification platform. Built with **FastAPI**, **React (TypeScript + Vite)**, **PyMuPDF**, **Google Gemini AI**, and **PostgreSQL**.

---

## 📌 Table of Contents
- [Overview](#-overview)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Repository Structure](#-repository-structure)
- [Architecture Overview](#-architecture-overview)
- [Local Development Setup](#-local-development-setup)
  - [Prerequisites](#prerequisites)
  - [Docker Compose (Full Stack)](#1-docker-compose-full-stack)
  - [Manual Local Setup (Backend + Frontend)](#2-manual-local-setup)
- [Environment Variables](#-environment-variables)
- [Deployed URLs](#-deployed-urls)
- [Application Screenshots](#-application-screenshots)
- [Known Limitations & Roadmap](#-known-limitations--roadmap)
- [Verification & Testing](#-verification--testing)

---

## 🔬 Overview

Clinical document review is frequently bottlenecked by unstructured notes, scanned non-searchable PDFs, and missing vital indicators. The **AI Clinical Document Reviewer** automates clinical intake by extracting structured medical entities (demographics, vitals, diagnoses, medications, allergies, physical exam findings), synthesizing cohesive executive narrative summaries, and deterministically detecting safety risks such as drug-allergy contraindications and missing critical parameters.

---

## 🚀 Key Features

- **Multi-Modal Ingestion**: Ingests raw clinical text, digital and scanned clinical study protocols (PDF), and medical imagery (JPG/PNG).
- **Fast Digital Extraction with Vision Fallback**:
  - Digital PDFs are extracted via [`pdf_extractor.py`](backend/app/services/pdf_extractor.py) using PyMuPDF (`fitz`).
  - Low-density / scanned PDFs (< 50 characters) automatically trigger 150 DPI page rendering and fallback to the multimodal vision OCR pipeline.
- **Strict Clinical Schema Enforcement**:
  - Outputs strictly validated schema models: [`StructuredClinicalReport`](backend/app/schemas/clinical_report.py) covering patient demographics, vital signs, diagnoses, active medications (with dosage and route), allergies, observations, and clinical concerns.
- **Intelligent Safety & Contraindication Engine**:
  - Deterministic clinical cross-checking ([`_cross_validate_and_enrich_flags`](backend/app/services/clinical_extractor.py#L70)) against known allergen families (Penicillins, Sulfas, NSAIDs, Opioids).
  - Explicitly detects and populates `missing_information` (e.g., absent vital signs, missing drug dosages, unrecorded demographics) and `potential_inconsistencies`.
  - Sets `requires_review = True` on any clinical ambiguity.
- **Distinct Executive Narrative Synthesis**:
  - Generates a coherent narrative summary via a dedicated second-stage prompt ([`generate_clinical_summary`](backend/app/services/clinical_extractor.py#L202)) rather than truncating raw JSON.
- **Self-Healing AI Retries & Error Protection**:
  - Automatically recovers from invalid JSON with a 1-step repair prompt ([`repair_json_output`](backend/app/services/gemini_client.py#L90)).
  - Uniform error envelope `{ success: false, error: { code, message, details } }` with **zero raw stack trace leakage** to clients.
- **Interactive Modern UI**:
  - Tabs for Text / PDF / Image inputs with 1-click sample templates.
  - Live short-interval polling (1.5s) on [`ReportDetailPage.tsx`](frontend/src/pages/ReportDetailPage.tsx) until completion.
  - Prominent narrative summary, danger banners for contraindications, and collapsible clinical schema sections.

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, React Router v6, Lucide Icons, Custom CSS Design System |
| **Backend API** | FastAPI, Python 3.11, Pydantic v2, Pydantic Settings, Starlette |
| **Database & ORM** | PostgreSQL 16, SQLAlchemy 2.0 (with JSONB support), Alembic Migrations |
| **AI / ML & OCR** | Google GenAI SDK (Gemini 2.5 Flash), PyMuPDF (`fitz`), Pillow (PIL) |
| **Testing** | Pytest, Pytest-Asyncio, Starlette TestClient (31 automated unit tests) |
| **Deployment & Containers** | Multi-stage Dockerfiles, Docker Compose, Nginx Alpine, Render, Railway, Vercel |

---

## 📂 Repository Structure

```
.
├── backend/                              # FastAPI Application
│   ├── alembic/                          # Alembic migration environment & revisions
│   │   └── versions/
│   │       └── 0001_create_reports_table.py
│   ├── app/
│   │   ├── api/v1/                       # Versioned API routes
│   │   │   ├── endpoints/
│   │   │   │   ├── health.py             # Service & DB connectivity probe
│   │   │   │   └── reports.py            # POST/GET reports endpoints
│   │   │   └── router.py                 # API v1 router registry
│   │   ├── core/                         # Core infrastructure
│   │   │   ├── config.py                 # Pydantic Settings & env loading
│   │   │   ├── error_handlers.py         # Global consistent exception handlers
│   │   │   ├── exceptions.py             # Domain exceptions (DocumentQualityError, etc.)
│   │   │   └── logging_config.py         # Structured JSON logging
│   │   ├── crud/
│   │   │   └── crud_report.py            # CRUD operations with pagination & ordering
│   │   ├── db/
│   │   │   ├── base.py                   # Model registry for migrations
│   │   │   └── session.py                # Engine & SessionLocal factory
│   │   ├── models/
│   │   │   └── report.py                 # SQLAlchemy Report model & enums
│   │   ├── schemas/                      # Pydantic Schemas
│   │   │   ├── clinical_report.py        # StructuredClinicalReport schema
│   │   │   ├── error.py                  # ErrorDetail & ErrorResponse envelope
│   │   │   └── report.py                 # ReportCreate, ReportResponse, ReportList
│   │   └── services/                     # Business & AI Services
│   │       ├── clinical_extractor.py     # AI extraction, cross-validation, summary
│   │       ├── gemini_client.py          # Gemini API wrapper with JSON repair
│   │       ├── pdf_extractor.py          # PyMuPDF text & page rendering
│   │       ├── report_processor.py       # Asynchronous background worker
│   │       ├── storage.py                # File upload storage
│   │       └── vision_pipeline.py        # Vision OCR fallback pipeline
│   ├── scripts/
│   │   └── seed_reports.py               # Synthetic clinical samples seed script
│   ├── tests/                            # 31 unit test suite
│   ├── Dockerfile                        # Multi-stage Python 3.11 container
│   ├── entrypoint.sh                     # Migration & startup runner
│   └── requirements.txt                  # Python dependencies
├── frontend/                             # React + Vite SPA
│   ├── src/
│   │   ├── api/
│   │   │   ├── apiClient.ts              # Configurable typed fetch client (FormData + errors)
│   │   │   ├── health.ts                 # Health API integration
│   │   │   └── reports.ts                # Report submission & retrieval methods
│   │   ├── pages/
│   │   │   ├── HistoryPage.tsx           # Paginated reports table with safety tags
│   │   │   ├── HomePage.tsx              # Architectural overview dashboard
│   │   │   ├── NotFoundPage.tsx          # 404 page
│   │   │   ├── ReportDetailPage.tsx      # Polling report view with collapsible sections
│   │   │   └── SubmitPage.tsx            # Multi-modal submission form with samples
│   │   ├── routes/
│   │   │   └── index.tsx                 # Route declarations
│   │   ├── App.tsx                       # Root layout & navigation bar
│   │   └── index.css                     # Medical dark/light design system
│   ├── Dockerfile                        # Multi-stage Nginx container
│   ├── nginx.conf                        # SPA client routing & static cache configuration
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── .env.example                          # Universal environment variable template
├── .gitignore
├── AI_ML_DESIGN.md                       # In-depth AI/ML extraction documentation
├── ARCHITECTURE.md                       # Comprehensive architecture & Mermaid diagram
├── TECHNICAL_DECISIONS.md                # Trade-offs & technical justifications
├── docker-compose.yml                    # Multi-service stack with PostgreSQL persistence
├── railway.json                          # Railway deployment configuration
├── render.yaml                           # Render Blueprint Infrastructure-as-Code
└── vercel.json                           # Vercel SPA deployment configuration
```

---

## 🏛️ Architecture Overview

The system processes clinical documents through a decoupled, asynchronous pipeline:
1. **Client Submission**: React frontend uploads text, image, or PDF via `POST /api/v1/reports`.
2. **Initial Persistence & Enqueueing**: FastAPI validates file headers, persists a row with `status=pending`, and triggers [`process_report_task`](backend/app/services/report_processor.py#L18) as a background task.
3. **Document Ingestion & Extraction**:
   - Digital PDF: Extracted via PyMuPDF.
   - Scanned PDF: Rendered to images (150 DPI) when text < 50 characters, routed to vision pipeline.
   - Image: Multimodal vision extraction.
4. **Structured AI Extraction & Self-Healing**: Calls Gemini 2.5 Flash with strict JSON schema. If invalid JSON is returned, a repair prompt executes automatically.
5. **Safety Cross-Validation**: Python clinical rules engine checks allergen maps, missing vitals, and incomplete prescriptions, setting `requires_review = True` and populating flags.
6. **Narrative Summary Generation**: Distinct prompt synthesizes medical narrative prose.
7. **Storage & Live Updates**: Report updates to `status=completed` (or `status=failed` with clear message). Frontend polls every 1.5s until ready.

---

## ⚙️ Local Development Setup

### Prerequisites
- **Node.js**: v18+ (tested on Node v20/v22)
- **Python**: 3.10 or 3.11
- **Docker & Docker Compose** (optional for containerized run)
- **Gemini API Key** (optional, offline heuristic fallback mode available)

---

### 1. Docker Compose (Full Stack)

To run Backend, Frontend, and PostgreSQL with persistent storage:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ai-clinical-reviewer.git
cd ai-clinical-reviewer

# 2. Configure Environment Variables
cp .env.example .env
# Open .env and insert your GEMINI_API_KEY if available

# 3. Boot all containers
docker compose up --build
```

**Service URLs:**
- **Frontend SPA**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **Platform Health Probe**: [http://localhost:8000/health](http://localhost:8000/health)

---

### 2. Manual Local Setup

#### Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# (Optional) Seed sample clinical documents
python scripts/seed_reports.py

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup
```bash
cd frontend

# Install Node modules
npm install

# Start Vite development server
npm run dev
```
*(Open [http://localhost:5173](http://localhost:5173))*

---

## 🔐 Environment Variables

Refer to [`.env.example`](.env.example) for the complete list of configurable variables:

| Variable | Scope | Description | Default |
|---|---|---|---|
| `PROJECT_NAME` | Backend | Application title | `"AI Clinical Document Reviewer"` |
| `API_V1_STR` | Backend | Prefix for API version 1 | `"/api/v1"` |
| `ENVIRONMENT` | Backend | Runtime mode (`development`, `production`) | `"development"` |
| `CORS_ORIGINS` | Backend | Allowed CORS origins JSON list | `["http://localhost:5173","http://localhost:3000"]` |
| `POSTGRES_SERVER` | Backend | PostgreSQL host | `"localhost"` (or `"postgres"`) |
| `POSTGRES_PORT` | Backend | PostgreSQL port | `5432` |
| `POSTGRES_USER` | Backend | PostgreSQL username | `"postgres"` |
| `POSTGRES_PASSWORD` | Backend | PostgreSQL password | `"postgres"` |
| `POSTGRES_DB` | Backend | Database name | `"clinical_reviewer"` |
| `DATABASE_URL` | Backend | Managed connection string (Render / Railway) | `None` |
| `GEMINI_API_KEY` | Backend | Google AI Studio API Key | `None` (uses heuristic fallback) |
| `GEMINI_MODEL` | Backend | Gemini model identifier | `"gemini-2.5-flash"` |
| `MAX_FILE_SIZE_MB` | Backend | Maximum allowed file upload size | `25` |
| `MIN_PDF_TEXT_LENGTH_THRESHOLD` | Backend | Scanned PDF detection threshold | `50` |
| `RUN_MIGRATIONS` | Backend | Run Alembic migrations on startup | `true` |
| `VITE_API_BASE_URL` | Frontend | Backend API base endpoint | `"http://localhost:8000/api/v1"` |

---

## 🌐 Deployed URLs

- **Frontend Application (Vercel)**: `https://ai-clinical-reviewer.vercel.app` *(Placeholder)*
- **Backend API (Render / Railway)**: `https://ai-clinical-reviewer-api.onrender.com` *(Placeholder)*
- **API Documentation**: `https://ai-clinical-reviewer-api.onrender.com/api/v1/docs` *(Placeholder)*
- **Liveness Health Check**: `https://ai-clinical-reviewer-api.onrender.com/health` *(Placeholder)*

---

## 📸 Application Screenshots

> *Placeholder: Add application screenshots here demonstrating the multi-modal submission form, live report polling, contraindication alert banners, and collapsible clinical schema sections.*

| Submission View | Report Detail & Safety Flags |
|:---:|:---:|
| `![Submission View Placeholder](docs/images/submit_view.png)` | `![Report Detail Placeholder](docs/images/report_detail.png)` |

| Reports History | Collapsible Clinical Accordions |
|:---:|:---:|
| `![History View Placeholder](docs/images/history_view.png)` | `![Accordions Placeholder](docs/images/accordions.png)` |

---

## ⚠️ Known Limitations & Roadmap

1. **Distributed Task Broker**: Background tasks currently use FastAPI's built-in in-memory `BackgroundTasks`. For multi-instance horizontal scaling, migrating to Celery / ARQ backed by Redis is recommended.
2. **Medical Ontology Mapping**: Extracted medication and disease names are currently retained in clinical natural language. Future iterations will map entities to **RxNorm**, **SNOMED-CT**, and **ICD-10-CM** concept IDs.
3. **Multi-Page Heavy Scans**: Scanned PDF rendering is currently set to 150 DPI for speed. Very large 50+ page protocols should be processed with page-by-page streaming chunking.
4. **HIPAA Audit & User Authentication**: The current version focuses on extraction and safety algorithms. Production clinical deployments require OAuth2/OIDC role-based access control and immutable audit logs.

---

## 🧪 Verification & Testing

The backend includes 31 automated test cases across 5 test suites:
- [`test_api_reports.py`](backend/tests/test_api_reports.py): Multi-modal submission, PyMuPDF extraction, vision fallback, pagination, error states.
- [`test_clinical_extractor.py`](backend/tests/test_clinical_extractor.py): Clean, sparse, and contradictory notes, document quality guardrails, JSON repair prompts, distinct summary generation.
- [`test_crud_report.py`](backend/tests/test_crud_report.py): Database operations, descending order pagination, status transitions.
- [`test_error_handling.py`](backend/tests/test_error_handling.py): Consistent error envelopes, zero stack trace leakage.
- [`test_seed.py`](backend/tests/test_seed.py): Synthetic sample database seeding idempotency.

Run tests:
```bash
cd backend
pytest -v
```
*(31 passed in ~2.5s)*
