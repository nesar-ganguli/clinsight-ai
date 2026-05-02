import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import close_all_sessions


TEST_DB_PATH = Path(__file__).resolve().parent / "test_clinsight.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")

from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models.allergy_intolerance import AllergyIntolerance
from app.models.condition import Condition
from app.models.curated_record_source import CuratedRecordSource
from app.models.encounter import Encounter
from app.models.ingestion_batch import IngestionBatch
from app.models.medication_request import MedicationRequest
from app.models.observation import Observation
from app.models.patient import Patient
from app.models.patient_source_identifier import PatientSourceIdentifier
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


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=engine)
    yield
    close_all_sessions()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(autouse=True)
def clear_database():
    db = SessionLocal()
    try:
        db.query(CuratedRecordSource).delete()
        db.query(StagingClinicalResource).delete()
        db.query(StagingPatientIdentity).delete()
        db.query(RawHospitalAllergy).delete()
        db.query(RawHospitalMedication).delete()
        db.query(RawHospitalObservation).delete()
        db.query(RawHospitalDiagnosis).delete()
        db.query(RawHospitalEncounter).delete()
        db.query(RawHospitalPatient).delete()
        db.query(RawAllergy).delete()
        db.query(RawMedication).delete()
        db.query(RawLab).delete()
        db.query(RawDiagnosis).delete()
        db.query(RawEncounter).delete()
        db.query(RawProvider).delete()
        db.query(RawDepartment).delete()
        db.query(RawPatient).delete()
        db.query(PatientSourceIdentifier).delete()
        db.query(AllergyIntolerance).delete()
        db.query(Condition).delete()
        db.query(Encounter).delete()
        db.query(MedicationRequest).delete()
        db.query(Observation).delete()
        db.query(Patient).delete()
        db.query(IngestionBatch).delete()
        db.query(SourceSystem).delete()
        db.commit()
        yield
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
