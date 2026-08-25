"""Make FHIR child resource keys source-aware.

Revision ID: 0008_source_aware_fhir_keys
Revises: 0007_audit_event_details
Create Date: 2026-08-25 00:00:00
"""

from alembic import op


revision = "0008_source_aware_fhir_keys"
down_revision = "0007_audit_event_details"
branch_labels = None
depends_on = None


RESOURCE_CONSTRAINTS = (
    (
        "conditions",
        "uq_conditions_patient_fhir_condition_id",
        "uq_conditions_patient_source_fhir_condition_id",
        "fhir_condition_id",
    ),
    (
        "observations",
        "uq_observations_patient_fhir_observation_id",
        "uq_observations_patient_source_fhir_observation_id",
        "fhir_observation_id",
    ),
    (
        "encounters",
        "uq_encounters_patient_fhir_encounter_id",
        "uq_encounters_patient_source_fhir_encounter_id",
        "fhir_encounter_id",
    ),
    (
        "medication_requests",
        "uq_medication_requests_patient_fhir_medication_request_id",
        "uq_med_requests_patient_source_fhir_id",
        "fhir_medication_request_id",
    ),
    (
        "allergy_intolerances",
        "uq_allergy_intolerances_patient_fhir_allergy_id",
        "uq_allergy_intolerances_patient_source_fhir_allergy_id",
        "fhir_allergy_id",
    ),
)


def upgrade() -> None:
    for table_name, old_name, new_name, fhir_id_column in RESOURCE_CONSTRAINTS:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(old_name, type_="unique")
            batch_op.create_unique_constraint(
                new_name,
                ["patient_id", "source_system", fhir_id_column],
            )


def downgrade() -> None:
    for table_name, old_name, new_name, fhir_id_column in reversed(RESOURCE_CONSTRAINTS):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(new_name, type_="unique")
            batch_op.create_unique_constraint(
                old_name,
                ["patient_id", fhir_id_column],
            )
