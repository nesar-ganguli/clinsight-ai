"""Initial ClinSight schema

Revision ID: 0001_initial_clinsight_schema
Revises: None
Create Date: 2026-04-22 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_clinsight_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fhir_patient_id", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("birth_date", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fhir_patient_id")
    )
    op.create_index(op.f("ix_patients_id"), "patients", ["id"], unique=False)
    op.create_index(op.f("ix_patients_fhir_patient_id"), "patients", ["fhir_patient_id"], unique=False)
    op.create_index(op.f("ix_patients_full_name"), "patients", ["full_name"], unique=False)

    op.create_table(
        "conditions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("fhir_condition_id", sa.String(length=255), nullable=True),
        sa.Column("condition_code", sa.String(length=100), nullable=True),
        sa.Column("condition_name", sa.String(length=255), nullable=True),
        sa.Column("clinical_status", sa.String(length=100), nullable=True),
        sa.Column("onset_date", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", "fhir_condition_id", name="uq_conditions_patient_fhir_condition_id")
    )
    op.create_index(op.f("ix_conditions_id"), "conditions", ["id"], unique=False)
    op.create_index(op.f("ix_conditions_patient_id"), "conditions", ["patient_id"], unique=False)
    op.create_index(op.f("ix_conditions_condition_code"), "conditions", ["condition_code"], unique=False)

    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("fhir_observation_id", sa.String(length=255), nullable=True),
        sa.Column("observation_code", sa.String(length=100), nullable=True),
        sa.Column("observation_name", sa.String(length=255), nullable=True),
        sa.Column("value", sa.String(length=255), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("effective_date", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", "fhir_observation_id", name="uq_observations_patient_fhir_observation_id")
    )
    op.create_index(op.f("ix_observations_id"), "observations", ["id"], unique=False)
    op.create_index(op.f("ix_observations_patient_id"), "observations", ["patient_id"], unique=False)
    op.create_index(op.f("ix_observations_observation_code"), "observations", ["observation_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_observations_observation_code"), table_name="observations")
    op.drop_index(op.f("ix_observations_patient_id"), table_name="observations")
    op.drop_index(op.f("ix_observations_id"), table_name="observations")
    op.drop_table("observations")

    op.drop_index(op.f("ix_conditions_condition_code"), table_name="conditions")
    op.drop_index(op.f("ix_conditions_patient_id"), table_name="conditions")
    op.drop_index(op.f("ix_conditions_id"), table_name="conditions")
    op.drop_table("conditions")

    op.drop_index(op.f("ix_patients_full_name"), table_name="patients")
    op.drop_index(op.f("ix_patients_fhir_patient_id"), table_name="patients")
    op.drop_index(op.f("ix_patients_id"), table_name="patients")
    op.drop_table("patients")
