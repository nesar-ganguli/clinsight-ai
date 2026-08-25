"""Resolve canonical patients through source-specific identifiers.

Revision ID: 0009_canonical_patient_identity
Revises: 0008_source_aware_fhir_keys
Create Date: 2026-08-25 00:00:00
"""

from typing import Optional

import sqlalchemy as sa
from alembic import op


revision = "0009_canonical_patient_identity"
down_revision = "0008_source_aware_fhir_keys"
branch_labels = None
depends_on = None


PATIENT_FHIR_UNIQUE_NAME = "uq_patients_fhir_patient_id"
OLD_IDENTIFIER_UNIQUE_NAME = "uq_patient_source_identifiers_source_type_value"
NEW_IDENTIFIER_UNIQUE_NAME = "uq_patient_source_identifiers_source_value"


def upgrade() -> None:
    _drop_patient_fhir_id_uniqueness()

    with op.batch_alter_table("patient_source_identifiers") as batch_op:
        batch_op.drop_constraint(OLD_IDENTIFIER_UNIQUE_NAME, type_="unique")
        batch_op.create_unique_constraint(
            NEW_IDENTIFIER_UNIQUE_NAME,
            ["source_system_id", "identifier_value"],
        )

    _backfill_source_identifiers()


def downgrade() -> None:
    with op.batch_alter_table("patient_source_identifiers") as batch_op:
        batch_op.drop_constraint(NEW_IDENTIFIER_UNIQUE_NAME, type_="unique")
        batch_op.create_unique_constraint(
            OLD_IDENTIFIER_UNIQUE_NAME,
            ["source_system_id", "identifier_type", "identifier_value"],
        )

    with op.batch_alter_table("patients") as batch_op:
        batch_op.create_unique_constraint(
            PATIENT_FHIR_UNIQUE_NAME,
            ["fhir_patient_id"],
        )


def _drop_patient_fhir_id_uniqueness() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        naming_convention = {
            "uq": "uq_%(table_name)s_%(column_0_name)s",
        }
        with op.batch_alter_table(
            "patients",
            naming_convention=naming_convention,
        ) as batch_op:
            batch_op.drop_constraint(PATIENT_FHIR_UNIQUE_NAME, type_="unique")
        return

    unique_name = _patient_fhir_unique_constraint_name(bind)
    if unique_name:
        op.drop_constraint(unique_name, "patients", type_="unique")


def _backfill_source_identifiers() -> None:
    op.execute(
        sa.text(
            """
            insert into patient_source_identifiers (
                patient_id,
                source_system_id,
                identifier_type,
                identifier_value,
                assigning_authority
            )
            select
                patients.id,
                source_systems.id,
                'fhir_patient_id',
                patients.fhir_patient_id,
                'FHIR Bundle'
            from patients
            join source_systems
              on source_systems.name = patients.source_system
            where patients.fhir_patient_id is not null
              and not exists (
                  select 1
                  from patient_source_identifiers
                  where patient_source_identifiers.source_system_id = source_systems.id
                    and patient_source_identifiers.identifier_value = patients.fhir_patient_id
              )
            """
        )
    )


def _patient_fhir_unique_constraint_name(bind) -> Optional[str]:
    inspector = sa.inspect(bind)
    for constraint in inspector.get_unique_constraints("patients"):
        if constraint.get("column_names") == ["fhir_patient_id"]:
            return constraint.get("name")
    return None
