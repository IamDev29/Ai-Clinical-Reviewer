# System Architecture

This document provides a comprehensive technical overview of the **AI Clinical Document Reviewer** architecture, detailing data flow, system boundaries, asynchronous background processing, structured schema enforcement, and cloud deployment topology.

---

## 🏗️ End-to-End Architecture Diagram

```mermaid
flowchart TD
    subgraph ClientLayer["🖥️ Frontend Client Layer (React + Vite SPA)"]
        UI_Submit["Submit View\n(Text / PDF / Image Tabs)"]
        UI_Detail["Report Detail View\n(Real-Time Polling)"]
        UI_History["History View\n(Paginated Records)"]
        API_Client["Shared API Client\n(apiClient.ts)"]
        
        UI_Submit --> API_Client
        UI_Detail --> API_Client
        UI_History --> API_Client
    end

    subgraph APILayer["⚡ Backend API Gateway (FastAPI Python 3.11)"]
        CORS["CORS Middleware"]
        ErrHandler["Global Error Handlers\n(Consistent JSON Envelope)"]
        Router_V1["/api/v1 Router"]
        HealthEndpoint["/health & /api/v1/health\n(Liveness & DB Ping)"]
        ReportsEndpoint["POST /api/v1/reports\nGET /api/v1/reports/{id}\nGET /api/v1/reports"]
        
        API_Client -->|HTTP / JSON / Multipart| CORS
        CORS --> Router_V1
        Router_V1 --> ReportsEndpoint
        Router_V1 --> HealthEndpoint
        ReportsEndpoint -.-> ErrHandler
    end

    subgraph StorageLayer["💾 Document Ingestion & Storage"]
        FileStorage["File Storage Service\n(storage.py)"]
        UploadsDisk[("storage/uploads/\n(Persistent Volume)")]
        
        ReportsEndpoint -->|Save Uploads| FileStorage
        FileStorage --> UploadsDisk
    end

    subgraph WorkerLayer["⚙️ Asynchronous Background Worker"]
        BG_Task["FastAPI BackgroundTasks\n(process_report_task)"]
        PDF_Extractor["PyMuPDF Extractor\n(pdf_extractor.py)"]
        Vision_Fallback["Page Renderer & Vision OCR\n(vision_pipeline.py)"]
        
        ReportsEndpoint -->|Enqueue Report ID| BG_Task
        BG_Task -->|Digital PDF| PDF_Extractor
        PDF_Extractor -->|< 50 chars threshold| Vision_Fallback
    end

    subgraph AIMLLayer["🧠 AI / ML Extraction & Safety Pipeline"]
        QualityGate["Quality Gate\n(check_document_quality)"]
        GeminiWrapper["Gemini Client\n(gemini_client.py)"]
        JSONRepair["Self-Healing JSON Repair Loop\n(repair_json_output)"]
        SafetyRules["Clinical Safety Rule Engine\n(_cross_validate_and_enrich_flags)"]
        SummaryGen["Narrative Summary Generator\n(generate_clinical_summary)"]
        
        BG_Task --> QualityGate
        QualityGate --> GeminiWrapper
        GeminiWrapper -.->|On JSON Decode/Validation Error| JSONRepair
        JSONRepair -.->|Repaired Schema| SafetyRules
        GeminiWrapper -->|Structured Output| SafetyRules
        SafetyRules --> SummaryGen
    end

    subgraph ExternalLLM["☁️ External Foundation Model"]
        GeminiAPI["Google Gemini 2.5 Flash API\n(google-genai SDK)"]
        GeminiWrapper <-->|JSON Mode / Multimodal| GeminiAPI
    end

    subgraph DBLayer["🗄️ Persistence Layer (PostgreSQL 16)"]
        SQLAlchemyORM["SQLAlchemy 2.0 ORM\n(models/report.py)"]
        AlembicEnv["Alembic Migrations\n(0001_create_reports_table.py)"]
        PostgresDB[("PostgreSQL 16 Database\n(reports table with JSONB)")]
        
        HealthEndpoint -->|SELECT 1 Ping| PostgresDB
        ReportsEndpoint -->|1. Insert status=pending| SQLAlchemyORM
        BG_Task -->|2. Update status=processing| SQLAlchemyORM
        SummaryGen -->|3. Update status=completed / JSONB| SQLAlchemyORM
        SQLAlchemyORM --> PostgresDB
        AlembicEnv --> PostgresDB
    end

    style ClientLayer fill:#111827,stroke:#3b82f6,stroke-width:2px,color:#fff
    style APILayer fill:#111827,stroke:#10b981,stroke-width:2px,color:#fff
    style WorkerLayer fill:#111827,stroke:#f59e0b,stroke-width:2px,color:#fff
    style AIMLLayer fill:#111827,stroke:#a855f7,stroke-width:2px,color:#fff
    style DBLayer fill:#111827,stroke:#06b6d4,stroke-width:2px,color:#fff
    style ExternalLLM fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff
```

---

## 🔄 Component Breakdown & Data Flow

### 1. Client Layer ([`frontend/src`](frontend/src))
- **`SubmitPage.tsx`**: Provides multi-modal tabs for raw clinical notes, PDF protocols, and medical scans/images. Preloaded with quick sample notes demonstrating *clean*, *sparse*, and *contradictory* encounters.
- **`apiClient.ts`**: Centralized HTTP client wrapping `fetch` with automatic `FormData` detection, configurable base URL (`VITE_API_BASE_URL`), and standardized parsing of the `{ success: false, error: { code, message } }` envelope.
- **`ReportDetailPage.tsx`**: Mounts with an automatic 1.5-second polling timer (`fetchReport`) that checks report status (`pending` ➔ `processing` ➔ `completed`/`failed`) until termination. Renders structured accordion cards and prominent warning banners without displaying raw JSON.
- **`HistoryPage.tsx`**: Paginated table listing past clinical reviews sorted with newest first, displaying type badges, timestamp, contraindication warning tags, and one-click inspection.

---

### 2. API & Routing Layer ([`backend/app/api/v1`](backend/app/api/v1))
- **`reports.py`**:
  - `POST /api/v1/reports`: Validates multipart inputs, rejects unsupported extensions or empty requests with HTTP 400, persists a new row in PostgreSQL with `status=pending`, and dispatches the background extraction job.
  - `GET /api/v1/reports/{report_id}`: Retrieves single report with structured clinical findings and executive narrative summary.
  - `GET /api/v1/reports`: Retrieves paginated reports ordered by `created_at DESC, id DESC`.
- **`health.py` & `main.py`**:
  - Direct root probe `GET /health` and versioned probe `GET /api/v1/health` executing active `SELECT 1` database query pings for cloud orchestrator liveness checks (Render, Railway, Kubernetes, Docker).
- **`error_handlers.py`**:
  - Global exception interceptors for `StarletteHTTPException`, `RequestValidationError`, `DocumentQualityError`, `ClinicalProcessingError`, and generic `Exception`.
  - Guarantees that **zero raw stack traces** or internal exception class names are returned to clients.

---

### 3. Asynchronous Worker & Ingestion Layer ([`backend/app/services`](backend/app/services))
- **`report_processor.py` (`process_report_task`)**:
  - Runs in the background decoupled from the HTTP response cycle.
  - Transitions report status from `pending` ➔ `processing` ➔ `completed` (or `failed`).
- **`pdf_extractor.py` (`extract_pdf_content`)**:
  - Opens PDF streams with PyMuPDF (`fitz.open`).
  - Measures total character length across all pages.
  - If text density < `settings.MIN_PDF_TEXT_LENGTH_THRESHOLD` (50 chars), classifies document as a scanned/image PDF, renders each page to a 150 DPI PNG, and routes to vision OCR.
- **`storage.py` (`save_upload_file`)**:
  - Sanitizes filenames and persists files into `storage/uploads/` with UUID prefixes.

---

## 🧠 AI / ML Pipeline Lifecycle

The AI/ML extraction layer operates in 4 sequential stages:

```mermaid
sequenceDiagram
    autonumber
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant Worker as Background Task
    participant Quality as Quality Gate
    participant Gemini as Gemini 2.5 Flash
    participant Safety as Safety Rule Engine
    participant DB as PostgreSQL

    UI->>API: POST /api/v1/reports (Multipart Note/PDF/Image)
    API->>DB: INSERT INTO reports (status='pending')
    API->>Worker: Enqueue process_report_task(report_id)
    API-->>UI: 201 Created (Report ID, status='pending')
    
    Worker->>DB: UPDATE reports SET status='processing'
    Worker->>Quality: check_document_quality(extracted_text, image_path)
    
    alt Quality Check Fails (Empty/Gibberish)
        Quality-->>Worker: raise DocumentQualityError
        Worker->>DB: UPDATE reports SET status='failed', error_message='...'
    else Quality Check Passes
        Worker->>Gemini: generate_structured_json(prompt, schema=StructuredClinicalReport)
        
        alt Malformed JSON / Schema Validation Error
            Gemini-->>Worker: ValidationError / JSONDecodeError
            Worker->>Gemini: repair_json_output(original_text, error, schema)
            Gemini-->>Worker: Valid Repaired JSON
        else Successful Extraction
            Gemini-->>Worker: Valid Structured JSON
        end
        
        Worker->>Safety: _cross_validate_and_enrich_flags(structured_report)
        Note over Safety: Checks Allergy vs Medication conflicts<br/>Checks Missing Vitals / Demographics / Dosages<br/>Sets requires_review = True if flagged
        
        Worker->>Gemini: generate_clinical_summary(source_text, structured_report)
        Gemini-->>Worker: Dedicated Executive Narrative Prose
        
        Worker->>DB: UPDATE reports SET status='completed', structured_report=JSONB, report_summary='...'
    end

    loop Every 1.5s until completed
        UI->>API: GET /api/v1/reports/{id}
        API->>DB: SELECT * FROM reports WHERE id=id
        API-->>UI: 200 OK (status='completed', structured_report, summary)
    end
```

---

## 🗄️ Database Schema & Persistence

The PostgreSQL database schema is managed via Alembic revision [`0001_create_reports_table.py`](backend/alembic/versions/0001_create_reports_table.py):

| Column | Type | Description | Index |
|---|---|---|---|
| `id` | `INTEGER` (SERIAL) | Primary Key Autoincrement | Primary Index (`ix_reports_id`) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | UTC record creation timestamp | B-Tree Index (`ix_reports_created_at`) |
| `status` | `VARCHAR(50)` | Enum: `pending`, `processing`, `completed`, `failed` | B-Tree Index (`ix_reports_status`) |
| `input_type` | `VARCHAR(50)` | Enum: `text`, `image`, `pdf` | B-Tree Index (`ix_reports_input_type`) |
| `raw_input_ref` | `TEXT` | Raw text payload or file system storage path | — |
| `extracted_text` | `TEXT` | Extracted plain text or PyMuPDF / Vision OCR output | — |
| `report_summary` | `TEXT` | Dedicated executive narrative summary | — |
| `structured_report` | `JSONB` | Structured clinical schema (demographics, vitals, meds, flags) | — |
| `error_message` | `TEXT` | Nullable error explanation for failed runs | — |

---

## 🌐 Deployment Topology

- **Docker Compose**:
  - `clinical_reviewer_postgres` (Port 5432) with persistent volume `postgres_data:/var/lib/postgresql/data`.
  - `clinical_reviewer_backend` (Port 8000) running multi-stage Python 3.11 with automatic Alembic migrations on startup.
  - `clinical_reviewer_frontend` (Port 3000) served by Nginx Alpine with SPA routing.
- **Render / Railway (Backend & DB)**:
  - Docker container running `entrypoint.sh` binding dynamically to `$PORT`.
  - Connected to Managed PostgreSQL via `DATABASE_URL`.
  - Healthcheck monitored at `/health`.
- **Vercel (Frontend SPA)**:
  - Deployed as static edge bundle with client-side SPA routing rewrites configured via `vercel.json`.
