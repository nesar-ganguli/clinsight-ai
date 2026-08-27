from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_ai_insights import router as ai_insights_router
from app.api.routes_audit import router as audit_router
from app.api.routes_auth import router as auth_router
from app.api.routes_demo import router as demo_router
from app.api.routes_external_fhir import router as external_fhir_router
from app.api.routes_ingestion_review import router as ingestion_review_router
from app.api.routes_upload import router as upload_router
from app.api.routes_patient import router as patient_router
from app.api.routes_patient_chat import router as patient_chat_router
from app.api.routes_pipeline_runs import router as pipeline_runs_router
from app.api.routes_quality import router as quality_router
from app.core.config import settings

from app.models.patient import Patient
from app.models.condition import Condition
from app.models.observation import Observation
from app.models.encounter import Encounter
from app.models.medication_request import MedicationRequest
from app.models.allergy_intolerance import AllergyIntolerance
from app.models.audit_log import AuditLog
from app.models.curated_record_source import CuratedRecordSource
from app.models.ingestion_batch import IngestionBatch
from app.models.patient_source_identifier import PatientSourceIdentifier
from app.models.pipeline_run import PipelineRun
from app.models.quarantine_record import QuarantineRecord
from app.models.raw_hospital import (
    RawHospitalAllergy,
    RawHospitalDiagnosis,
    RawHospitalEncounter,
    RawHospitalMedication,
    RawHospitalObservation,
    RawHospitalPatient,
)
from app.models.raw_operational import (
    RawAllergy,
    RawDepartment,
    RawDiagnosis,
    RawEncounter,
    RawLab,
    RawMedication,
    RawPatient,
    RawProvider,
)
from app.models.source_system import SourceSystem
from app.models.staging import StagingClinicalResource, StagingPatientIdentity
from app.models.user import User

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router, prefix=settings.api_v1_prefix, tags=["Auth"])
app.include_router(audit_router, prefix=settings.api_v1_prefix, tags=["Audit"])
app.include_router(external_fhir_router, prefix=settings.api_v1_prefix, tags=["External FHIR"])
app.include_router(ingestion_review_router, prefix=settings.api_v1_prefix, tags=["Ingestion Review"])
app.include_router(upload_router, prefix=settings.api_v1_prefix, tags=["Upload"])
app.include_router(patient_router, prefix=settings.api_v1_prefix, tags=["Patients"])
app.include_router(patient_chat_router, prefix=settings.api_v1_prefix, tags=["Patient Chat"])
app.include_router(pipeline_runs_router, prefix=settings.api_v1_prefix, tags=["Pipeline Runs"])
app.include_router(quality_router, prefix=settings.api_v1_prefix, tags=["Quality"])
app.include_router(ai_insights_router, prefix=settings.api_v1_prefix, tags=["AI Insights"])
app.include_router(demo_router, prefix=settings.api_v1_prefix, tags=["Demo"])


@app.get("/")
def root():
    return {"message": "ClinSight AI backend is running"}
