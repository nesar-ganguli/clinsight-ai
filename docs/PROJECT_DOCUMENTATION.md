# ClinSight AI Project Documentation

## Executive Summary

ClinSight AI is a full-stack Software + AI clinical data application that ingests FHIR Bundle JSON files, stores normalized patient records, surfaces data quality alerts, and generates grounded AI-style clinical insights with source citations and hallucination checks.

The core product story is:

1. Upload a FHIR Bundle.
2. Parse and persist structured clinical records.
3. Search patients in a Next.js workspace.
4. Open a longitudinal chart.
5. Review allergies, timeline events, quality alerts, care gaps, inconsistencies, and grounded AI summaries.
6. Evaluate whether every generated claim is backed by source records.

This is intentionally not a generic chatbot wrapper. The AI layer is a deterministic grounded insight engine designed to make clinical AI feel credible, inspectable, and safe.

## Quantified Project Snapshot

| Area | Count / Result |
| --- | ---: |
| Backend framework | FastAPI |
| Frontend framework | Next.js 15 + React 19 |
| Database support | SQLite locally, PostgreSQL via Docker Compose |
| Supported FHIR resource types | 6 |
| SQLAlchemy data models | 6 |
| API routes | 6 API routes + root health route |
| Backend service modules | 5 |
| Pydantic schema modules | 5 |
| Frontend route pages | 2 |
| Reusable frontend panels/components | 3 |
| Seeded FHIR bundles | 4 |
| Seeded demo patients | 4 |
| Seeded clinical resources, excluding Bundle wrappers | 29 |
| Special allergy stress-test patient | 1 patient with 5 allergies |
| Backend tests | 10 passing |
| Measured source lines across app/tests/scripts | 3,434 lines |
| Docker services | 5 services |
| Demo personas | 3 |

## Technology Stack

Backend:

- FastAPI
- SQLAlchemy ORM
- Alembic migrations
- Pydantic / pydantic-settings
- Uvicorn
- Pytest
- SQLite for local development
- PostgreSQL for Docker Compose demo

Frontend:

- Next.js 15
- React 19
- TypeScript
- Server-rendered patient detail route
- Client-side upload, patient directory, and demo role panels

Dev/demo infrastructure:

- Docker Compose
- Seed scripts
- Metrics script
- Mermaid architecture diagram
- SVG product screenshots

## Product Capabilities

### 1. FHIR Bundle Ingestion

The backend accepts FHIR Bundle JSON uploads at:

```text
POST /api/upload
```

Supported FHIR resources:

1. Patient
2. Condition
3. Observation
4. Encounter
5. MedicationRequest
6. AllergyIntolerance

The ingestion path:

```text
Upload JSON -> validate Bundle -> parse FHIR resources -> normalize fields -> persist to database -> return import summary
```

Import behavior:

- Creates a patient if the FHIR patient ID is new.
- Updates an existing patient if the FHIR patient ID already exists.
- Replaces child records on update so repeated uploads are idempotent.
- Returns resource counts by FHIR resource type.

Relevant files:

- `backend/app/api/routes_upload.py`
- `backend/app/services/fhir_parser.py`
- `backend/app/services/ingestion.py`

## Data Model

ClinSight stores 6 normalized clinical entities:

| Model | Purpose |
| --- | --- |
| Patient | Demographics and FHIR patient ID |
| Condition | Problem list / diagnoses |
| Observation | Vitals and clinical observations |
| Encounter | Visits and timeline context |
| MedicationRequest | Medication activity |
| AllergyIntolerance | Allergy and sensitivity records |

Patient relationships:

```text
Patient
  -> conditions
  -> observations
  -> encounters
  -> medication_requests
  -> allergies
```

## API Surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Backend health check |
| POST | `/api/upload` | Upload and ingest FHIR Bundle |
| GET | `/api/patients` | List/search patients |
| GET | `/api/patients/{patient_id}` | Fetch longitudinal patient record |
| GET | `/api/patients/{patient_id}/quality-alerts` | Fetch chart quality alerts |
| GET | `/api/patients/{patient_id}/ai-insights` | Fetch grounded AI insight report |
| GET | `/api/demo-users` | Fetch demo personas/roles |

## Frontend Experience

### Dashboard

The dashboard includes:

- FHIR Bundle upload panel
- Patient directory with search
- Demo personas panel
- Link into individual patient charts after upload

### Patient Detail Page

The patient page includes:

- Patient name/header card
- Demographics
- Allergy chips in the name card
- `+N more` allergy hover/focus popover when more than 3 allergies exist
- Grounded AI summary
- Source citation chips
- Longitudinal timeline
- Care gap suggestions
- Chart inconsistency detection
- Grounding and hallucination-risk evaluation
- Quality alerts
- Resource inventory

Allergy display rule:

```text
If 0 allergies: show "No allergies documented"
If 1-3 allergies: show all allergies
If more than 3 allergies: show first 3 + "+N more"
On hover/focus over "+N more": show remaining allergies
```

The stress-test patient `Avery Brooks` has 5 allergies, so the UI shows:

```text
3 allergy chips + "+2 more"
```

## AI / Insight Logic

The AI layer is currently a grounded clinical reasoning engine, not an external LLM call.

That means:

- It does not invent free-form claims.
- It only uses structured records stored in the database.
- Every summary claim includes source citation IDs.
- Every care gap and inconsistency cites source records.
- The evaluation layer checks for unsupported claims and unresolved citations.

Insight report endpoint:

```text
GET /api/patients/{patient_id}/ai-insights
```

The report includes:

1. `summary_sections`
2. `inconsistencies`
3. `care_gaps`
4. `citations`
5. `evaluation`

### Structured Summary Generation

The summary engine builds sections such as:

- Patient overview
- Problem list
- Recent observations
- Medication activity
- Allergies

Each claim includes:

```json
{
  "id": "condition-1",
  "text": "Hypertension is documented as active with onset 2024-08-20.",
  "citation_ids": ["Condition:6"]
}
```

### Chart Inconsistency Detection

Implemented inconsistency checks include:

- Encounter end time before start time
- Conflicting observation values for the same code and effective date
- Same condition appearing as both active and resolved/inactive
- Same medication appearing as both active and stopped

The seeded `Priya Nair` bundle intentionally triggers multiple inconsistency scenarios.

### Care Gap Suggestions

Implemented care-gap logic includes:

- Diabetes documented but no A1c observation found
- Hypertension documented but no blood pressure observation found
- Active conditions but no encounter context
- Active conditions but no active medications
- No allergy records found
- Data quality warnings that should be resolved before clinical handoff

Example:

```text
If diabetes condition exists AND no A1c observation exists:
  suggest "Review A1c monitoring"
  cite the diabetes condition record
```

### Hallucination / Grounding Evaluation

The insight evaluation reports:

- Number of grounded claims
- Number of unsupported claims
- Number of unresolved citations
- Source coverage
- Hallucination risk
- Checklist of grounding rules

Current measured result:

```text
unsupported_claims: 0
unresolved_citations: 0
hallucination_risk: low for all 4 demo patients
```

## Seeded Demo Data

The project includes 4 FHIR Bundle files:

| File | Patient | Resource Count | Demo Purpose |
| --- | --- | ---: | --- |
| `patient_bundle_1.json` | John Doe | 8 | Standard chronic-care chart |
| `patient_bundle_2.json` | Elena Martinez | 2 | Sparse chart with missing coverage |
| `patient_bundle_3.json` | Priya Nair | 9 | Inconsistency stress test |
| `patient_bundle_5_allergies.json` | Avery Brooks | 10 | Allergy overflow UI stress test |

Total seeded clinical resources, excluding Bundle wrappers:

```text
8 + 2 + 9 + 10 = 29 resources
```

## Demo Personas

The app includes 3 interview personas:

| Persona | Role | Demo Lens |
| --- | --- | --- |
| Dr. Maya Chen | CMIO reviewer | AI credibility, safety posture, alert usefulness |
| Alex Rivera | Care coordinator | Care gaps and follow-up preparation |
| Sam Patel | Clinical data lead | Ingestion quality, metrics, and source coverage |

Endpoint:

```text
GET /api/demo-users
```

These are product walkthrough roles, not production authentication.

## Metrics

Metrics are generated by:

```bash
cd backend
source .venv/bin/activate
python scripts/measure_demo_metrics.py
```

Latest measured output:

```json
{
  "ingestion_speed": {
    "average_ms": 4.33,
    "fastest_ms": 2.34,
    "slowest_ms": 8.9
  },
  "alert_precision": {
    "expected_alert_count": 5,
    "predicted_alert_count": 5,
    "true_positive_count": 5,
    "precision": 1.0,
    "recall": 1.0
  },
  "summary_evaluation": {
    "patients_evaluated": 4,
    "average_grounded_claims": 7.25,
    "unsupported_claims": 0,
    "unresolved_citations": 0,
    "hallucination_risk_distribution": {
      "low": 4
    }
  }
}
```

Per-bundle ingestion timing:

| Bundle | Resources | Time |
| --- | ---: | ---: |
| `patient_bundle_1.json` | 8 | 8.90 ms |
| `patient_bundle_2.json` | 2 | 2.34 ms |
| `patient_bundle_3.json` | 9 | 2.91 ms |
| `patient_bundle_5_allergies.json` | 10 | 3.16 ms |

## Testing

Backend test command:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

Current result:

```text
10 passed in 0.13s
```

Test coverage areas:

- FHIR parser behavior
- Upload API behavior
- Idempotent patient updates
- Patient search
- Quality alert output
- AI insight report citations
- Demo users endpoint

## Docker / Deployment Readiness

The Docker Compose setup includes 5 services:

| Service | Purpose |
| --- | --- |
| `db` | PostgreSQL database |
| `backend` | FastAPI API server |
| `frontend` | Next.js app |
| `seed` | Demo data seeding tool |
| `metrics` | Demo metrics reporting tool |

Run full app:

```bash
docker compose up --build
```

Seed demo data:

```bash
docker compose --profile tools run --rm seed
```

Run metrics:

```bash
docker compose --profile tools run --rm metrics
```

## Local Run Commands

Backend:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python scripts/seed_demo_data.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
/Users/nesarganguli/.nvm/versions/node/v20.19.2/bin/node node_modules/next/dist/bin/next dev -H 127.0.0.1 -p 3000
```

Open:

```text
http://localhost:3000
```

## Resume Positioning

Strong resume bullet:

```text
Built ClinSight AI, a full-stack clinical intelligence platform using FastAPI, Next.js, PostgreSQL, SQLAlchemy, Alembic, Docker, and FHIR pipelines to ingest patient bundles, surface chart quality alerts, and generate citation-backed AI clinical summaries with hallucination-risk evaluation.
```

Second bullet:

```text
Implemented a grounded AI insight engine for structured patient summaries, chart inconsistency detection, care gap suggestions, source-record citations, and repeatable metrics across 4 seeded demo patients, 29 clinical resources, 10 passing backend tests, and 0 unsupported generated claims.
```

Short technical tagline:

```text
FastAPI, Next.js, TypeScript, PostgreSQL, SQLAlchemy, Alembic, Docker, FHIR, clinical data quality, grounded AI evaluation
```

## Why This Project Is Strong

This project is strong for Software + AI roles because it demonstrates:

- Real backend engineering
- Real frontend product implementation
- Domain-specific data modeling
- FHIR data handling
- Database persistence and migrations
- AI safety and grounding thinking
- Repeatable evaluation metrics
- Dockerized demo readiness
- Interview storytelling

Most AI portfolio projects stop at prompt-in, text-out. ClinSight AI shows the harder and more valuable pattern:

```text
structured data -> clinical reasoning -> cited output -> evaluation
```
