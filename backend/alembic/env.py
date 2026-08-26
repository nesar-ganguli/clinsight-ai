from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.database import Base
from app.models.allergy_intolerance import AllergyIntolerance
from app.models.audit_log import AuditLog
from app.models.condition import Condition
from app.models.curated_record_source import CuratedRecordSource
from app.models.encounter import Encounter
from app.models.ingestion_batch import IngestionBatch
from app.models.medication_request import MedicationRequest
from app.models.observation import Observation
from app.models.patient import Patient
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

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
