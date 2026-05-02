# ClinSight AI

ClinSight AI is an interview-ready clinical data app for importing FHIR Bundles, reviewing longitudinal patient charts, and generating grounded clinical intelligence with source citations.

The product goal is simple: make AI-assisted chart review feel credible. Every summary claim, care gap suggestion, and chart inconsistency is tied back to stored source records, then checked by an evaluation layer for unsupported claims and unresolved citations.

## Product Screens

![ClinSight AI dashboard](docs/screenshots/dashboard.svg)

![ClinSight AI patient insights](docs/screenshots/patient-insights.svg)

## What It Shows

- FHIR Bundle ingestion for Patient, Condition, Observation, Encounter, MedicationRequest, and AllergyIntolerance resources
- Patient directory with search
- Longitudinal chart view
- Data quality alerts for missing demographics, missing resources, and incomplete clinical records
- Grounded AI-style patient summaries with citations
- Chart inconsistency detection
- Care gap suggestions
- Summary evaluation checks for hallucination risk
- Demo roles for CMIO, care coordination, and clinical data leadership walkthroughs
- Repeatable demo metrics for ingestion speed, alert precision, and summary quality

## Architecture

```mermaid
flowchart LR
  clinician[Clinician or Interviewer]
  frontend[Next.js Frontend\nPatient workspace and insight views]
  backend[FastAPI Backend\nFHIR ingestion and APIs]
  parser[FHIR Parser\nPatient, conditions, observations,\nencounters, medications, allergies]
  rules[Grounded Insight Engine\nSummaries, inconsistencies,\ncare gaps, evaluation]
  quality[Quality Checker\nCompleteness and structured alerts]
  db[(PostgreSQL\nClinical record store)]
  samples[Seeded FHIR Bundles\nDemo patient datasets]
  metrics[Metrics Script\nIngestion speed, alert precision,\nsummary grounding]

  clinician --> frontend
  frontend --> backend
  backend --> parser
  parser --> db
  backend --> quality
  backend --> rules
  quality --> db
  rules --> db
  samples --> backend
  metrics --> backend
  metrics --> db
```

The source diagram is also available at `docs/architecture.mmd`.

## Run With Docker

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

Seed demo patients:

```bash
docker compose --profile tools run --rm seed
```

Run interview metrics:

```bash
docker compose --profile tools run --rm metrics
```

## Run Locally

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirement.txt
printf "DATABASE_URL=sqlite:///./clinsight.db\n" > .env
alembic upgrade head
python scripts/seed_demo_data.py
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Next.js 15 needs Node 18.18 or newer. This repo has been verified with Node 20.

## Demo Users

The app exposes demo personas at `GET /api/demo-users` and renders them on the dashboard.

- Dr. Maya Chen, CMIO reviewer: reviews AI credibility, safety posture, and alert usefulness
- Alex Rivera, care coordinator: uses care gaps and inconsistency findings for follow-up prep
- Sam Patel, clinical data lead: evaluates ingestion quality, source coverage, and metrics

These are interview personas, not production authentication.

## Seeded Sample Datasets

The seeded demo uses three FHIR Bundles in `backend/sample_data`:

- `patient_bundle_1.json`: chronic-care chart with hypertension, diabetes, observations, medication, encounter, and allergy
- `patient_bundle_2.json`: sparse diabetes chart with intentional missing demographics and coverage gaps
- `patient_bundle_3.json`: chart with intentional contradictions, including conflicting condition statuses, duplicate observation values, encounter date conflict, and medication status conflict

## Metrics

Run:

```bash
cd backend
source .venv/bin/activate
python scripts/measure_demo_metrics.py
```

The metrics report includes:

- `ingestion_speed`: per-bundle and aggregate ingestion timings
- `alert_precision`: expected vs. predicted quality alert counts, precision, and recall
- `summary_evaluation`: grounded claim averages, unsupported claim count, unresolved citation count, and hallucination risk distribution

These metrics are intentionally small and repeatable so an interviewer can rerun them live.

## Test And Build

Backend:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

Frontend:

```bash
cd frontend
npx tsc --noEmit
npm run build
```

If your default shell still points to Node 17, switch to Node 20 before running the frontend build.
