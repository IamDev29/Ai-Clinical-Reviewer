# Technical Decisions, Trade-Offs & Architecture Justification

This document details the architectural decisions, technology selections, trade-offs, and future improvements for the **AI Clinical Document Reviewer**.

---

## 🏛️ 1. Technology Selection & Architectural Justifications

### A. Frontend Architecture: React 18 + TypeScript + Vite
- **Selection**: React 18 with TypeScript, Vite bundler, React Router v6, Lucide React icons, and a custom medical CSS design system.
- **Why Vite over Create React App / Next.js?**
  - Instant Hot Module Replacement (HMR) and sub-second builds via Rollup/esbuild.
  - Clean SPA architecture that deploys effortlessly to edge CDNs (Vercel/Cloudflare/Nginx) without server-side Node.js runtime overhead.
- **Why Short-Interval Polling over WebSockets / SSE?**
  - **Decision**: Implemented 1.5-second polling on [`ReportDetailPage.tsx`](frontend/src/pages/ReportDetailPage.tsx) until status reaches `completed` or `failed`.
  - **Justification**: Clinical document review jobs typically complete in 1 to 4 seconds. Polling is completely stateless, immune to proxy/load-balancer connection drops, requires zero WebSocket heartbeat maintenance on serverless/container hosts, and simplified multi-region edge deployment.

---

### B. Backend API: FastAPI + Python 3.11
- **Selection**: FastAPI with Pydantic v2 and Python 3.11 runtime.
- **Why FastAPI over Django / Flask?**
  - **Asynchronous Throughput**: Native `async`/`await` support for non-blocking file streaming and background task dispatch.
  - **Pydantic v2 Type Safety**: Zero-copy JSON serialization via Pydantic Core (Rust-based), ensuring sub-millisecond schema validation for clinical models.
  - **Automatic OpenAPI / Swagger Generation**: Interactive documentation out-of-the-box at `/api/v1/docs`.
  - **BackgroundTasks**: Provides lightweight asynchronous task dispatch for document extraction without requiring a heavy distributed worker fleet for single-instance deployments.

---

### C. Database Architecture: PostgreSQL 16 + SQLAlchemy 2.0 + Alembic
- **Selection**: PostgreSQL 16 with JSONB column support, managed via SQLAlchemy 2.0 and Alembic migrations ([`0001_create_reports_table.py`](backend/alembic/versions/0001_create_reports_table.py)).
- **Why Hybrid Relational + JSONB?**
  - **Relational Columns** (`id`, `created_at`, `status`, `input_type`): Provide strict indexing, ACID transactions, and sub-millisecond paginated sorting (`ORDER BY created_at DESC, id DESC`).
  - **JSONB Column** (`structured_report`): Clinical records possess highly variable entity structures (varying medication lists, allergen profiles, physical exam findings). PostgreSQL JSONB offers full binary indexing (GIN) and schema flexibility without requiring dozens of sparse join tables.

---

### D. Document Ingestion: PyMuPDF (`fitz`) with Vision OCR Fallback
- **Selection**: PyMuPDF (`fitz`) for digital extraction; Pillow rendering (150 DPI) for scanned document fallback.
- **Why PyMuPDF over pypdf / pdfminer?**
  - **Speed**: PyMuPDF (C-based MuPDF binding) is up to 10x faster than pure-Python extractors.
  - **Rendering Capability**: Directly renders PDF pages to pixel pixmaps (`page.get_pixmap()`), enabling seamless automatic fallback for image-only/scanned documents without requiring external CLI tools like Poppler.

---

### E. AI / ML Strategy: Gemini 2.5 Flash + Hybrid Safety Guardrails
- **Selection**: Google Gemini 2.5 Flash (`gemini-2.5-flash`) with structured JSON mode, two-stage narrative synthesis, and Python rule-based safety cross-checks.
- **Why Gemini 2.5 Flash?**
  - High reasoning capability, low latency (< 1s time-to-first-token), multimodal image support, and native schema compliance (`response_schema=StructuredClinicalReport`).
- **Why Two-Stage Prompting (Extraction ➔ Summary)?**
  - Single-prompt generation of both JSON and prose summary often causes models to compromise on one or the other.
  - In our architecture, [`extract_structured_clinical_data`](backend/app/services/clinical_extractor.py#L125) focuses purely on exhaustive entity extraction (temperature 0.1), while [`generate_clinical_summary`](backend/app/services/clinical_extractor.py#L202) focuses on synthesis and clinician communication (temperature 0.2).
- **Why Deterministic Safety Rules ([`_cross_validate_and_enrich_flags`](backend/app/services/clinical_extractor.py#L70))?**
  - LLMs can occasionally miss subtle drug-allergy interactions. Layering a deterministic rule engine ensures critical contraindications (e.g. Penicillin allergy + Amoxicillin) and missing vitals are **guaranteed to be flagged 100% of the time**.

---

## ⚖️ 2. Key Architectural Trade-Offs

| Decision | Pros | Cons / Trade-offs | Mitigation Implemented |
|---|---|---|---|
| **FastAPI `BackgroundTasks` vs Celery + Redis** | Zero infrastructure overhead; no Redis/RabbitMQ instance needed for local and basic cloud deployment. | Tasks run in the same process memory; tasks do not survive worker process crashes. | Decoupled worker function ([`process_report_task`](backend/app/services/report_processor.py#L18)) can be swapped to Celery/ARQ with zero changes to extraction logic. |
| **JSONB Storage for Structured Findings** | Schema flexibility across oncology, cardiology, and general notes; fast document retrieval in single query. | Querying deep nested JSON fields in SQL requires specific JSONB operators (`->`, `->>`). | Indexed core query columns (`status`, `input_type`, `created_at`) relationally. |
| **Client Polling vs Server-Sent Events (SSE)** | Stateless, works behind all cloud load balancers/CDNs without connection timeout issues. | Introduces minor network overhead during the 2-4 second processing window. | Short 1.5s interval with immediate timer cancellation upon completion. |
| **Self-Healing Repair Loop vs Immediate Failure** | Recovers from transient LLM syntax/formatting errors without user intervention. | Consumes an additional LLM call on malformed outputs. | Bounded to exactly 1 retry step; fails gracefully with structured domain error if repair fails. |

---

## 🔮 3. What Would Be Improved With More Time

### 1. Distributed Asynchronous Worker Fleet
- Replace in-process `BackgroundTasks` with **Celery** or **ARQ** backed by **Redis** or **RabbitMQ**.
- Enable dedicated worker pools with horizontal autoscaling, retry queues, and dead-letter queues (DLQ).

### 2. Clinical Terminology Normalization
- Integrate medical terminology normalization APIs to map extracted strings to standard biomedical ontologies:
  - Medications ➔ **RxNorm Concept Unique Identifiers (RxCUI)**.
  - Diagnoses / Conditions ➔ **SNOMED-CT** & **ICD-10-CM**.
  - Laboratory Measurements ➔ **LOINC codes**.

### 3. Longitudinal EHR Vector Search (RAG)
- Embed historical patient records into a vector database (**pgvector** or **Qdrant**).
- Enable semantic retrieval across prior clinical encounters to detect timeline discrepancies spanning multiple hospital admissions.

### 4. HIPAA Compliance & Audit Logging
- Implement **OAuth2 / OIDC** role-based access control (RBAC) separating Clinician and Auditor roles.
- Add an immutable audit log table recording all document submissions, views, and clinician review overrides with cryptographic signatures.

### 5. Automated End-to-End Testing
- Add **Playwright / Cypress** browser test suite testing the full UI submission flow, drag-and-drop file upload, live polling transitions, and accordion interactions.
