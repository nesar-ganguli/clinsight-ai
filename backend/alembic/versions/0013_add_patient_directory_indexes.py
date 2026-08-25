"""Add source-identifier index for patient directory search.

Revision ID: 0013_patient_directory_indexes
Revises: 0012_quarantine_records
Create Date: 2026-08-25 00:00:00
"""

from alembic import op


revision = "0013_patient_directory_indexes"
down_revision = "0012_quarantine_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_patient_source_identifiers_identifier_value"),
        "patient_source_identifiers",
        ["identifier_value"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_patient_source_identifiers_identifier_value"),
        table_name="patient_source_identifiers",
    )
