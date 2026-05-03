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

Run the full multi-source hospital pipeline:

```bash
docker compose --profile tools run --rm generate-hospital-data
docker compose --profile tools run --rm dbt-run
docker compose --profile tools run --rm generate-fhir
```

Run interview metrics:

```bash
docker compose --profile tools run --rm metrics
```

Run backend tests in Docker:

```bash
docker compose --profile tools run --rm backend-tests
```

You can tune the generated demo size without editing compose:

```bash
HOSPITAL_PATIENTS=250 HOSPITAL_SEED=7 PIPELINE_BATCH_ID=demo-batch-007 docker compose --profile tools run --rm generate-hospital-data
PIPELINE_BATCH_ID=demo-batch-007 docker compose --profile tools run --rm generate-fhir
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

## Synthetic Raw Hospital Data

Generate operational hospital-style source data into the `raw_*` tables only:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python scripts/generate_hospital_data.py --patients 1000 --seed 42
```

The generator creates linked raw patients, encounters, diagnoses, labs, medications, allergies, providers, and departments. It is reproducible by seed and includes controlled clinical examples such as diabetes patients missing A1c labs, hypertension patients missing blood pressure observations, conflicting lab values, and active diagnoses without active medications.

Use a stable batch id when you want repeatable reruns of the same raw load:

```bash
python scripts/generate_hospital_data.py --patients 1000 --seed 42 --ingestion-batch-id demo-hospital-batch-001
```

Rerunning the same `source_system` and `ingestion_batch_id` replaces only matching raw rows. It does not insert into or reset curated clinical tables.

## Full Local Pipeline With Docker Compose

Start PostgreSQL, FastAPI, and the Next.js app:

```bash
docker compose up --build
```

Then run each tool step in a second terminal:

```bash
docker compose --profile tools run --rm generate-hospital-data
docker compose --profile tools run --rm dbt-run
docker compose --profile tools run --rm generate-fhir
```

What each step does:

- `generate-hospital-data`: migrates the backend database, then loads synthetic operational rows into `raw_*` tables.
- `dbt-run`: builds and tests staging plus curated clinical dbt views in PostgreSQL.
- `generate-fhir`: reads curated clinical views and writes uploadable FHIR Bundle JSON to `backend/data/generated_fhir_bundles/`.
- `backend-tests`: runs the backend pytest suite in a container.
- `seed`: keeps the original seeded FHIR demo flow available.
- `metrics`: runs the optional interview metrics script.

Default pipeline values:

```bash
HOSPITAL_PATIENTS=1000
HOSPITAL_SEED=42
PIPELINE_BATCH_ID=synthetic-42-1000
FHIR_LIMIT=50
```

Override them inline when needed:

```bash
HOSPITAL_PATIENTS=100 PIPELINE_BATCH_ID=small-demo docker compose --profile tools run --rm generate-hospital-data
PIPELINE_BATCH_ID=small-demo FHIR_LIMIT=25 docker compose --profile tools run --rm generate-fhir
```

The app remains available at `http://localhost:3000`; the API remains available at `http://localhost:8000`.

## SMART Health IT External FHIR Import

ClinSight can also import demo patients from the public SMART Health IT HL7 FHIR R4 sandbox at `https://r4.smarthealthit.org`.

Admins and data reviewers can use the dashboard panel to search sandbox patients by name and import one patient at a time. The backend fetches Patient, Encounter, Condition, Observation, MedicationRequest, and AllergyIntolerance resources, wraps them as a FHIR Bundle, and sends that bundle through the same ingestion path as local JSON uploads.

API endpoints:

```bash
GET /api/external-fhir/smart/patients?search=smith&count=10
POST /api/external-fhir/smart/import/{patient_id}
```

Imported SMART records are tagged with source metadata as `SMART Health IT R4 Sandbox`, so patient charts, citations, and audit logs can distinguish them from local uploads and synthetic hospital data.

## Grounded Patient Chart Assistant

Patient charts include a grounded Q&A assistant for chart-review questions such as:

- `Has this patient had an A1c recently?`
- `Show recent blood pressure readings.`
- `What active medications are documented?`

The assistant uses structured patient records first, retrieves only patient-specific evidence, returns source citations, refuses diagnosis/treatment recommendations, and writes an audit event for each question. It works without an LLM by using deterministic grounded fallback answers.

To enable optional LLM-assisted wording with GitHub Models, set:

```bash
LLM_PROVIDER=github
GITHUB_MODELS_TOKEN=your_github_pat
GITHUB_MODELS_MODEL=openai/gpt-4o-mini
```

The backend still validates citation IDs and falls back to deterministic answers if the LLM call fails or returns unsupported output. An OpenAI Responses API path is also supported with `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL`.

## dbt Staging Models

The `dbt/` project transforms raw operational hospital tables into clean staging views. It targets PostgreSQL and leaves the `raw_*` tables untouched.

Install dbt for Postgres:

```bash
python -m pip install -r dbt/requirements.txt
```

Create a local dbt profile:

```bash
cd dbt
cp profiles.example.yml profiles.yml
```

Set connection values as environment variables if they differ from the example defaults:

```bash
export CLINSIGHT_DBT_HOST=localhost
export CLINSIGHT_DBT_PORT=5432
export CLINSIGHT_DBT_USER=clinsight
export CLINSIGHT_DBT_PASSWORD=clinsight
export CLINSIGHT_DBT_DBNAME=clinsight
export CLINSIGHT_DBT_SCHEMA=analytics
```

Run and test the staging models:

```bash
dbt debug --profiles-dir .
dbt run --profiles-dir . --select staging
dbt test --profiles-dir . --select staging
```

Run and test the curated clinical marts:

```bash
dbt run --profiles-dir . --select marts.clinical
dbt test --profiles-dir . --select marts.clinical
```

Generate uploadable FHIR Bundle JSON files from curated clinical records:

```bash
cd ../backend
source .venv/bin/activate
export DATABASE_URL=postgresql+psycopg2://clinsight:clinsight@localhost:5432/clinsight
python scripts/generate_fhir_bundles.py --limit 50 --output data/generated_fhir_bundles
```

Filter the export to a specific ingestion batch:

```bash
python scripts/generate_fhir_bundles.py --limit 50 --output data/generated_fhir_bundles --ingestion-batch-id synthetic-42-1000
```

If your raw hospital tables live outside the `public` schema, pass the raw schema explicitly:

```bash
dbt run --profiles-dir . --select staging --vars '{"raw_schema": "raw"}'
dbt test --profiles-dir . --select staging --vars '{"raw_schema": "raw"}'
```

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
