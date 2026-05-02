"""Add multi-source ingestion layers

Revision ID: 0003_multisource_layers
Revises: 0002_add_extended_fhir_resources
Create Date: 2026-05-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_multisource_layers"
down_revision = "0002_add_extended_fhir_resources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_systems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("system_type", sa.String(length=100), nullable=False),
        sa.Column("facility_name", sa.String(length=255), nullable=True),
        sa.Column("external_system_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_source_systems_name")
    )
    op.create_index(op.f("ix_source_systems_id"), "source_systems", ["id"], unique=False)
    op.create_index(op.f("ix_source_systems_external_system_id"), "source_systems", ["external_system_id"], unique=False)

    op.create_table(
        "ingestion_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_system_id", sa.Integer(), nullable=False),
        sa.Column("ingestion_type", sa.String(length=100), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=100), server_default="received", nullable=False),
        sa.Column("record_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_system_id"], ["source_systems.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_ingestion_batches_id"), "ingestion_batches", ["id"], unique=False)
    op.create_index(op.f("ix_ingestion_batches_source_system_id"), "ingestion_batches", ["source_system_id"], unique=False)
    op.create_index(op.f("ix_ingestion_batches_ingestion_type"), "ingestion_batches", ["ingestion_type"], unique=False)
    op.create_index(op.f("ix_ingestion_batches_content_hash"), "ingestion_batches", ["content_hash"], unique=False)

    op.create_table(
        "patient_source_identifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("source_system_id", sa.Integer(), nullable=False),
        sa.Column("identifier_type", sa.String(length=100), nullable=False),
        sa.Column("identifier_value", sa.String(length=255), nullable=False),
        sa.Column("assigning_authority", sa.String(length=255), nullable=True),
        sa.Column("last_seen_batch_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["last_seen_batch_id"], ["ingestion_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_system_id"], ["source_systems.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_system_id",
            "identifier_type",
            "identifier_value",
            name="uq_patient_source_identifiers_source_type_value"
        )
    )
    op.create_index(op.f("ix_patient_source_identifiers_id"), "patient_source_identifiers", ["id"], unique=False)
    op.create_index(op.f("ix_patient_source_identifiers_patient_id"), "patient_source_identifiers", ["patient_id"], unique=False)
    op.create_index(op.f("ix_patient_source_identifiers_source_system_id"), "patient_source_identifiers", ["source_system_id"], unique=False)

    op.create_table(
        "curated_record_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("curated_table_name", sa.String(length=100), nullable=False),
        sa.Column("curated_record_id", sa.Integer(), nullable=False),
        sa.Column("source_system_id", sa.Integer(), nullable=False),
        sa.Column("ingestion_batch_id", sa.Integer(), nullable=True),
        sa.Column("raw_table_name", sa.String(length=100), nullable=True),
        sa.Column("raw_record_id", sa.String(length=255), nullable=True),
        sa.Column("transform_version", sa.String(length=100), server_default="fhir-upload-v1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_batch_id"], ["ingestion_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_system_id"], ["source_systems.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_curated_record_sources_id"), "curated_record_sources", ["id"], unique=False)
    op.create_index(op.f("ix_curated_record_sources_curated_table_name"), "curated_record_sources", ["curated_table_name"], unique=False)
    op.create_index(op.f("ix_curated_record_sources_curated_record_id"), "curated_record_sources", ["curated_record_id"], unique=False)
    op.create_index(op.f("ix_curated_record_sources_source_system_id"), "curated_record_sources", ["source_system_id"], unique=False)
    op.create_index(op.f("ix_curated_record_sources_ingestion_batch_id"), "curated_record_sources", ["ingestion_batch_id"], unique=False)

    _create_raw_hospital_tables()
    _create_staging_tables()


def downgrade() -> None:
    _drop_staging_tables()
    _drop_raw_hospital_tables()

    op.drop_index(op.f("ix_curated_record_sources_ingestion_batch_id"), table_name="curated_record_sources")
    op.drop_index(op.f("ix_curated_record_sources_source_system_id"), table_name="curated_record_sources")
    op.drop_index(op.f("ix_curated_record_sources_curated_record_id"), table_name="curated_record_sources")
    op.drop_index(op.f("ix_curated_record_sources_curated_table_name"), table_name="curated_record_sources")
    op.drop_index(op.f("ix_curated_record_sources_id"), table_name="curated_record_sources")
    op.drop_table("curated_record_sources")

    op.drop_index(op.f("ix_patient_source_identifiers_source_system_id"), table_name="patient_source_identifiers")
    op.drop_index(op.f("ix_patient_source_identifiers_patient_id"), table_name="patient_source_identifiers")
    op.drop_index(op.f("ix_patient_source_identifiers_id"), table_name="patient_source_identifiers")
    op.drop_table("patient_source_identifiers")

    op.drop_index(op.f("ix_ingestion_batches_content_hash"), table_name="ingestion_batches")
    op.drop_index(op.f("ix_ingestion_batches_ingestion_type"), table_name="ingestion_batches")
    op.drop_index(op.f("ix_ingestion_batches_source_system_id"), table_name="ingestion_batches")
    op.drop_index(op.f("ix_ingestion_batches_id"), table_name="ingestion_batches")
    op.drop_table("ingestion_batches")

    op.drop_index(op.f("ix_source_systems_external_system_id"), table_name="source_systems")
    op.drop_index(op.f("ix_source_systems_id"), table_name="source_systems")
    op.drop_table("source_systems")


def _common_raw_columns(source_id_name: str) -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_system_id", sa.Integer(), nullable=False),
        sa.Column("ingestion_batch_id", sa.Integer(), nullable=True),
        sa.Column(source_id_name, sa.String(length=255), nullable=True),
        sa.Column("source_patient_id", sa.String(length=255), nullable=True),
        sa.Column("mrn", sa.String(length=255), nullable=True),
    ]


def _common_raw_tail() -> list[sa.Column]:
    return [
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("row_hash", sa.String(length=64), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def _raw_constraints(source_id_name: str, unique_name: str) -> list:
    return [
        sa.ForeignKeyConstraint(["ingestion_batch_id"], ["ingestion_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_system_id"], ["source_systems.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system_id", source_id_name, name=unique_name),
    ]


def _create_raw_hospital_tables() -> None:
    op.create_table(
        "raw_hospital_patients",
        *_common_raw_columns("source_record_id"),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("birth_date", sa.String(length=32), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        *_common_raw_tail(),
        *_raw_constraints("source_record_id", "uq_raw_hospital_patients_source_record")
    )
    _create_raw_indexes("raw_hospital_patients", ["source_record_id", "source_patient_id", "mrn", "full_name", "row_hash"])

    op.create_table(
        "raw_hospital_encounters",
        *_common_raw_columns("source_encounter_id"),
        sa.Column("encounter_status", sa.String(length=100), nullable=True),
        sa.Column("encounter_class", sa.String(length=100), nullable=True),
        sa.Column("encounter_type", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("admit_datetime", sa.String(length=64), nullable=True),
        sa.Column("discharge_datetime", sa.String(length=64), nullable=True),
        *_common_raw_tail(),
        *_raw_constraints("source_encounter_id", "uq_raw_hospital_encounters_source_encounter")
    )
    _create_raw_indexes("raw_hospital_encounters", ["source_encounter_id", "source_patient_id", "mrn", "row_hash"])

    op.create_table(
        "raw_hospital_diagnoses",
        *_common_raw_columns("source_diagnosis_id"),
        sa.Column("source_encounter_id", sa.String(length=255), nullable=True),
        sa.Column("diagnosis_type", sa.String(length=100), nullable=True),
        sa.Column("code_system", sa.String(length=100), nullable=True),
        sa.Column("diagnosis_code", sa.String(length=100), nullable=True),
        sa.Column("diagnosis_description", sa.String(length=255), nullable=True),
        sa.Column("clinical_status", sa.String(length=100), nullable=True),
        sa.Column("onset_date", sa.String(length=64), nullable=True),
        sa.Column("resolution_date", sa.String(length=64), nullable=True),
        *_common_raw_tail(),
        *_raw_constraints("source_diagnosis_id", "uq_raw_hospital_diagnoses_source_diagnosis")
    )
    _create_raw_indexes("raw_hospital_diagnoses", ["source_diagnosis_id", "source_patient_id", "source_encounter_id", "mrn", "diagnosis_code", "row_hash"])

    op.create_table(
        "raw_hospital_observations",
        *_common_raw_columns("source_observation_id"),
        sa.Column("source_encounter_id", sa.String(length=255), nullable=True),
        sa.Column("observation_type", sa.String(length=100), nullable=True),
        sa.Column("code_system", sa.String(length=100), nullable=True),
        sa.Column("observation_code", sa.String(length=100), nullable=True),
        sa.Column("observation_name", sa.String(length=255), nullable=True),
        sa.Column("value", sa.String(length=255), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("observed_at", sa.String(length=64), nullable=True),
        *_common_raw_tail(),
        *_raw_constraints("source_observation_id", "uq_raw_hospital_observations_source_observation")
    )
    _create_raw_indexes("raw_hospital_observations", ["source_observation_id", "source_patient_id", "source_encounter_id", "mrn", "observation_code", "row_hash"])

    op.create_table(
        "raw_hospital_medications",
        *_common_raw_columns("source_medication_id"),
        sa.Column("source_encounter_id", sa.String(length=255), nullable=True),
        sa.Column("medication_code", sa.String(length=100), nullable=True),
        sa.Column("medication_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("start_date", sa.String(length=64), nullable=True),
        sa.Column("end_date", sa.String(length=64), nullable=True),
        sa.Column("authored_on", sa.String(length=64), nullable=True),
        *_common_raw_tail(),
        *_raw_constraints("source_medication_id", "uq_raw_hospital_medications_source_medication")
    )
    _create_raw_indexes("raw_hospital_medications", ["source_medication_id", "source_patient_id", "source_encounter_id", "mrn", "medication_code", "row_hash"])

    op.create_table(
        "raw_hospital_allergies",
        *_common_raw_columns("source_allergy_id"),
        sa.Column("allergen_code", sa.String(length=100), nullable=True),
        sa.Column("allergen_name", sa.String(length=255), nullable=True),
        sa.Column("reaction", sa.String(length=255), nullable=True),
        sa.Column("severity", sa.String(length=100), nullable=True),
        sa.Column("criticality", sa.String(length=100), nullable=True),
        sa.Column("verification_status", sa.String(length=100), nullable=True),
        sa.Column("clinical_status", sa.String(length=100), nullable=True),
        sa.Column("recorded_date", sa.String(length=64), nullable=True),
        *_common_raw_tail(),
        *_raw_constraints("source_allergy_id", "uq_raw_hospital_allergies_source_allergy")
    )
    _create_raw_indexes("raw_hospital_allergies", ["source_allergy_id", "source_patient_id", "mrn", "allergen_code", "row_hash"])


def _create_raw_indexes(table_name: str, indexed_columns: list[str]) -> None:
    op.create_index(op.f(f"ix_{table_name}_id"), table_name, ["id"], unique=False)
    op.create_index(op.f(f"ix_{table_name}_source_system_id"), table_name, ["source_system_id"], unique=False)
    op.create_index(op.f(f"ix_{table_name}_ingestion_batch_id"), table_name, ["ingestion_batch_id"], unique=False)
    for column_name in indexed_columns:
        op.create_index(op.f(f"ix_{table_name}_{column_name}"), table_name, [column_name], unique=False)


def _drop_raw_hospital_tables() -> None:
    raw_indexes = {
        "raw_hospital_allergies": ["id", "source_system_id", "ingestion_batch_id", "source_allergy_id", "source_patient_id", "mrn", "allergen_code", "row_hash"],
        "raw_hospital_medications": ["id", "source_system_id", "ingestion_batch_id", "source_medication_id", "source_patient_id", "source_encounter_id", "mrn", "medication_code", "row_hash"],
        "raw_hospital_observations": ["id", "source_system_id", "ingestion_batch_id", "source_observation_id", "source_patient_id", "source_encounter_id", "mrn", "observation_code", "row_hash"],
        "raw_hospital_diagnoses": ["id", "source_system_id", "ingestion_batch_id", "source_diagnosis_id", "source_patient_id", "source_encounter_id", "mrn", "diagnosis_code", "row_hash"],
        "raw_hospital_encounters": ["id", "source_system_id", "ingestion_batch_id", "source_encounter_id", "source_patient_id", "mrn", "row_hash"],
        "raw_hospital_patients": ["id", "source_system_id", "ingestion_batch_id", "source_record_id", "source_patient_id", "mrn", "full_name", "row_hash"],
    }
    for table_name, columns in raw_indexes.items():
        for column_name in columns:
            op.drop_index(op.f(f"ix_{table_name}_{column_name}"), table_name=table_name)
        op.drop_table(table_name)


def _create_staging_tables() -> None:
    op.create_table(
        "staging_patient_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_system_id", sa.Integer(), nullable=False),
        sa.Column("ingestion_batch_id", sa.Integer(), nullable=True),
        sa.Column("raw_table_name", sa.String(length=100), nullable=True),
        sa.Column("raw_record_id", sa.String(length=255), nullable=True),
        sa.Column("source_patient_id", sa.String(length=255), nullable=True),
        sa.Column("mrn", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("birth_date", sa.String(length=32), nullable=True),
        sa.Column("candidate_patient_id", sa.Integer(), nullable=True),
        sa.Column("match_status", sa.String(length=100), server_default="pending", nullable=False),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_patient_id"], ["patients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ingestion_batch_id"], ["ingestion_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_system_id"], ["source_systems.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_staging_patient_identities_id"), "staging_patient_identities", ["id"], unique=False)
    op.create_index(op.f("ix_staging_patient_identities_source_system_id"), "staging_patient_identities", ["source_system_id"], unique=False)
    op.create_index(op.f("ix_staging_patient_identities_ingestion_batch_id"), "staging_patient_identities", ["ingestion_batch_id"], unique=False)
    op.create_index(op.f("ix_staging_patient_identities_source_patient_id"), "staging_patient_identities", ["source_patient_id"], unique=False)
    op.create_index(op.f("ix_staging_patient_identities_mrn"), "staging_patient_identities", ["mrn"], unique=False)
    op.create_index(op.f("ix_staging_patient_identities_candidate_patient_id"), "staging_patient_identities", ["candidate_patient_id"], unique=False)

    op.create_table(
        "staging_clinical_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_system_id", sa.Integer(), nullable=False),
        sa.Column("ingestion_batch_id", sa.Integer(), nullable=True),
        sa.Column("raw_table_name", sa.String(length=100), nullable=True),
        sa.Column("raw_record_id", sa.String(length=255), nullable=True),
        sa.Column("source_patient_id", sa.String(length=255), nullable=True),
        sa.Column("target_resource_type", sa.String(length=100), nullable=False),
        sa.Column("normalized_payload", sa.JSON(), nullable=True),
        sa.Column("validation_status", sa.String(length=100), server_default="pending", nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("curated_table_name", sa.String(length=100), nullable=True),
        sa.Column("curated_record_id", sa.Integer(), nullable=True),
        sa.Column("transform_version", sa.String(length=100), server_default="v1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_batch_id"], ["ingestion_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_system_id"], ["source_systems.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_staging_clinical_resources_id"), "staging_clinical_resources", ["id"], unique=False)
    op.create_index(op.f("ix_staging_clinical_resources_source_system_id"), "staging_clinical_resources", ["source_system_id"], unique=False)
    op.create_index(op.f("ix_staging_clinical_resources_ingestion_batch_id"), "staging_clinical_resources", ["ingestion_batch_id"], unique=False)
    op.create_index(op.f("ix_staging_clinical_resources_source_patient_id"), "staging_clinical_resources", ["source_patient_id"], unique=False)
    op.create_index(op.f("ix_staging_clinical_resources_target_resource_type"), "staging_clinical_resources", ["target_resource_type"], unique=False)
    op.create_index(op.f("ix_staging_clinical_resources_curated_record_id"), "staging_clinical_resources", ["curated_record_id"], unique=False)


def _drop_staging_tables() -> None:
    op.drop_index(op.f("ix_staging_clinical_resources_curated_record_id"), table_name="staging_clinical_resources")
    op.drop_index(op.f("ix_staging_clinical_resources_target_resource_type"), table_name="staging_clinical_resources")
    op.drop_index(op.f("ix_staging_clinical_resources_source_patient_id"), table_name="staging_clinical_resources")
    op.drop_index(op.f("ix_staging_clinical_resources_ingestion_batch_id"), table_name="staging_clinical_resources")
    op.drop_index(op.f("ix_staging_clinical_resources_source_system_id"), table_name="staging_clinical_resources")
    op.drop_index(op.f("ix_staging_clinical_resources_id"), table_name="staging_clinical_resources")
    op.drop_table("staging_clinical_resources")

    op.drop_index(op.f("ix_staging_patient_identities_candidate_patient_id"), table_name="staging_patient_identities")
    op.drop_index(op.f("ix_staging_patient_identities_mrn"), table_name="staging_patient_identities")
    op.drop_index(op.f("ix_staging_patient_identities_source_patient_id"), table_name="staging_patient_identities")
    op.drop_index(op.f("ix_staging_patient_identities_ingestion_batch_id"), table_name="staging_patient_identities")
    op.drop_index(op.f("ix_staging_patient_identities_source_system_id"), table_name="staging_patient_identities")
    op.drop_index(op.f("ix_staging_patient_identities_id"), table_name="staging_patient_identities")
    op.drop_table("staging_patient_identities")
