"""Add raw operational hospital tables

Revision ID: 0004_raw_operational
Revises: 0003_multisource_layers
Create Date: 2026-05-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_raw_operational"
down_revision = "0003_multisource_layers"
branch_labels = None
depends_on = None


RAW_TABLE_INDEXES = {
    "raw_patients": [
        "id",
        "source_system",
        "source_record_id",
        "ingestion_batch_id",
        "mrn",
        "enterprise_patient_id",
        "last_name",
    ],
    "raw_encounters": [
        "id",
        "source_system",
        "source_record_id",
        "ingestion_batch_id",
        "encounter_number",
        "mrn",
        "department_code",
        "attending_provider_id",
    ],
    "raw_diagnoses": [
        "id",
        "source_system",
        "source_record_id",
        "ingestion_batch_id",
        "encounter_number",
        "mrn",
        "diagnosis_code",
    ],
    "raw_labs": [
        "id",
        "source_system",
        "source_record_id",
        "ingestion_batch_id",
        "order_id",
        "encounter_number",
        "mrn",
        "lab_code",
    ],
    "raw_medications": [
        "id",
        "source_system",
        "source_record_id",
        "ingestion_batch_id",
        "order_id",
        "encounter_number",
        "mrn",
        "medication_code",
        "ordering_provider_id",
    ],
    "raw_allergies": [
        "id",
        "source_system",
        "source_record_id",
        "ingestion_batch_id",
        "mrn",
        "allergen_code",
    ],
    "raw_providers": [
        "id",
        "source_system",
        "source_record_id",
        "ingestion_batch_id",
        "provider_id",
        "npi",
        "last_name",
        "department_code",
    ],
    "raw_departments": [
        "id",
        "source_system",
        "source_record_id",
        "ingestion_batch_id",
        "department_code",
        "facility_code",
    ],
}


def upgrade() -> None:
    op.create_table(
        "raw_patients",
        *_source_columns(),
        sa.Column("mrn", sa.String(length=255), nullable=True),
        sa.Column("enterprise_patient_id", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.String(length=32), nullable=True),
        sa.Column("sex", sa.String(length=50), nullable=True),
        sa.Column("address_line", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_patients_source_record_batch"),
    )
    _create_indexes("raw_patients")

    op.create_table(
        "raw_encounters",
        *_source_columns(),
        sa.Column("encounter_number", sa.String(length=255), nullable=True),
        sa.Column("mrn", sa.String(length=255), nullable=True),
        sa.Column("department_code", sa.String(length=100), nullable=True),
        sa.Column("attending_provider_id", sa.String(length=255), nullable=True),
        sa.Column("encounter_type", sa.String(length=100), nullable=True),
        sa.Column("admit_datetime", sa.String(length=64), nullable=True),
        sa.Column("discharge_datetime", sa.String(length=64), nullable=True),
        sa.Column("discharge_disposition", sa.String(length=255), nullable=True),
        sa.Column("financial_class", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_encounters_source_record_batch"),
    )
    _create_indexes("raw_encounters")

    op.create_table(
        "raw_diagnoses",
        *_source_columns(),
        sa.Column("encounter_number", sa.String(length=255), nullable=True),
        sa.Column("mrn", sa.String(length=255), nullable=True),
        sa.Column("diagnosis_code", sa.String(length=100), nullable=True),
        sa.Column("diagnosis_description", sa.String(length=255), nullable=True),
        sa.Column("code_system", sa.String(length=100), nullable=True),
        sa.Column("diagnosis_type", sa.String(length=100), nullable=True),
        sa.Column("present_on_admission", sa.String(length=20), nullable=True),
        sa.Column("diagnosis_datetime", sa.String(length=64), nullable=True),
        sa.Column("ranking", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_diagnoses_source_record_batch"),
    )
    _create_indexes("raw_diagnoses")

    op.create_table(
        "raw_labs",
        *_source_columns(),
        sa.Column("order_id", sa.String(length=255), nullable=True),
        sa.Column("encounter_number", sa.String(length=255), nullable=True),
        sa.Column("mrn", sa.String(length=255), nullable=True),
        sa.Column("lab_code", sa.String(length=100), nullable=True),
        sa.Column("lab_name", sa.String(length=255), nullable=True),
        sa.Column("result_value", sa.String(length=255), nullable=True),
        sa.Column("result_numeric", sa.Float(), nullable=True),
        sa.Column("result_unit", sa.String(length=64), nullable=True),
        sa.Column("reference_range", sa.String(length=100), nullable=True),
        sa.Column("abnormal_flag", sa.String(length=50), nullable=True),
        sa.Column("result_status", sa.String(length=100), nullable=True),
        sa.Column("collected_at", sa.String(length=64), nullable=True),
        sa.Column("resulted_at", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_labs_source_record_batch"),
    )
    _create_indexes("raw_labs")

    op.create_table(
        "raw_medications",
        *_source_columns(),
        sa.Column("order_id", sa.String(length=255), nullable=True),
        sa.Column("encounter_number", sa.String(length=255), nullable=True),
        sa.Column("mrn", sa.String(length=255), nullable=True),
        sa.Column("medication_code", sa.String(length=100), nullable=True),
        sa.Column("medication_name", sa.String(length=255), nullable=True),
        sa.Column("dose", sa.String(length=100), nullable=True),
        sa.Column("route", sa.String(length=100), nullable=True),
        sa.Column("frequency", sa.String(length=100), nullable=True),
        sa.Column("order_status", sa.String(length=100), nullable=True),
        sa.Column("ordered_at", sa.String(length=64), nullable=True),
        sa.Column("start_datetime", sa.String(length=64), nullable=True),
        sa.Column("stop_datetime", sa.String(length=64), nullable=True),
        sa.Column("ordering_provider_id", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_medications_source_record_batch"),
    )
    _create_indexes("raw_medications")

    op.create_table(
        "raw_allergies",
        *_source_columns(),
        sa.Column("mrn", sa.String(length=255), nullable=True),
        sa.Column("allergen_code", sa.String(length=100), nullable=True),
        sa.Column("allergen_name", sa.String(length=255), nullable=True),
        sa.Column("allergen_type", sa.String(length=100), nullable=True),
        sa.Column("reaction", sa.String(length=255), nullable=True),
        sa.Column("severity", sa.String(length=100), nullable=True),
        sa.Column("allergy_status", sa.String(length=100), nullable=True),
        sa.Column("recorded_at", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_allergies_source_record_batch"),
    )
    _create_indexes("raw_allergies")

    op.create_table(
        "raw_providers",
        *_source_columns(),
        sa.Column("provider_id", sa.String(length=255), nullable=True),
        sa.Column("npi", sa.String(length=50), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("credentials", sa.String(length=100), nullable=True),
        sa.Column("specialty", sa.String(length=255), nullable=True),
        sa.Column("department_code", sa.String(length=100), nullable=True),
        sa.Column("employment_status", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_providers_source_record_batch"),
    )
    _create_indexes("raw_providers")

    op.create_table(
        "raw_departments",
        *_source_columns(),
        sa.Column("department_code", sa.String(length=100), nullable=True),
        sa.Column("department_name", sa.String(length=255), nullable=True),
        sa.Column("facility_code", sa.String(length=100), nullable=True),
        sa.Column("facility_name", sa.String(length=255), nullable=True),
        sa.Column("service_line", sa.String(length=255), nullable=True),
        sa.Column("location_type", sa.String(length=100), nullable=True),
        sa.Column("active_flag", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_departments_source_record_batch"),
    )
    _create_indexes("raw_departments")


def downgrade() -> None:
    for table_name in reversed(list(RAW_TABLE_INDEXES.keys())):
        for column_name in RAW_TABLE_INDEXES[table_name]:
            op.drop_index(op.f(f"ix_{table_name}_{column_name}"), table_name=table_name)
        op.drop_table(table_name)


def _source_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(length=255), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("ingestion_batch_id", sa.String(length=255), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def _create_indexes(table_name: str) -> None:
    for column_name in RAW_TABLE_INDEXES[table_name]:
        op.create_index(op.f(f"ix_{table_name}_{column_name}"), table_name, [column_name], unique=False)
