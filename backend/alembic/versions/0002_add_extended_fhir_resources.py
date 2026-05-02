"""Add extended FHIR resources

Revision ID: 0002_add_extended_fhir_resources
Revises: 0001_initial_clinsight_schema
Create Date: 2026-04-22 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_extended_fhir_resources"
down_revision = "0001_initial_clinsight_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "encounters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("fhir_encounter_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("encounter_class", sa.String(length=100), nullable=True),
        sa.Column("encounter_type", sa.String(length=255), nullable=True),
        sa.Column("period_start", sa.String(length=64), nullable=True),
        sa.Column("period_end", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", "fhir_encounter_id", name="uq_encounters_patient_fhir_encounter_id")
    )
    op.create_index(op.f("ix_encounters_id"), "encounters", ["id"], unique=False)
    op.create_index(op.f("ix_encounters_patient_id"), "encounters", ["patient_id"], unique=False)

    op.create_table(
        "medication_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("fhir_medication_request_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("intent", sa.String(length=100), nullable=True),
        sa.Column("medication_code", sa.String(length=100), nullable=True),
        sa.Column("medication_name", sa.String(length=255), nullable=True),
        sa.Column("authored_on", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "patient_id",
            "fhir_medication_request_id",
            name="uq_medication_requests_patient_fhir_medication_request_id"
        )
    )
    op.create_index(op.f("ix_medication_requests_id"), "medication_requests", ["id"], unique=False)
    op.create_index(op.f("ix_medication_requests_patient_id"), "medication_requests", ["patient_id"], unique=False)
    op.create_index(op.f("ix_medication_requests_medication_code"), "medication_requests", ["medication_code"], unique=False)

    op.create_table(
        "allergy_intolerances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("fhir_allergy_id", sa.String(length=255), nullable=True),
        sa.Column("clinical_status", sa.String(length=100), nullable=True),
        sa.Column("verification_status", sa.String(length=100), nullable=True),
        sa.Column("allergy_code", sa.String(length=100), nullable=True),
        sa.Column("allergy_name", sa.String(length=255), nullable=True),
        sa.Column("criticality", sa.String(length=100), nullable=True),
        sa.Column("recorded_date", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", "fhir_allergy_id", name="uq_allergy_intolerances_patient_fhir_allergy_id")
    )
    op.create_index(op.f("ix_allergy_intolerances_id"), "allergy_intolerances", ["id"], unique=False)
    op.create_index(op.f("ix_allergy_intolerances_patient_id"), "allergy_intolerances", ["patient_id"], unique=False)
    op.create_index(op.f("ix_allergy_intolerances_allergy_code"), "allergy_intolerances", ["allergy_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_allergy_intolerances_allergy_code"), table_name="allergy_intolerances")
    op.drop_index(op.f("ix_allergy_intolerances_patient_id"), table_name="allergy_intolerances")
    op.drop_index(op.f("ix_allergy_intolerances_id"), table_name="allergy_intolerances")
    op.drop_table("allergy_intolerances")

    op.drop_index(op.f("ix_medication_requests_medication_code"), table_name="medication_requests")
    op.drop_index(op.f("ix_medication_requests_patient_id"), table_name="medication_requests")
    op.drop_index(op.f("ix_medication_requests_id"), table_name="medication_requests")
    op.drop_table("medication_requests")

    op.drop_index(op.f("ix_encounters_patient_id"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_id"), table_name="encounters")
    op.drop_table("encounters")
