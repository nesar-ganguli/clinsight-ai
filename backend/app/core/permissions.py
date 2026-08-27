ROLE_PERMISSIONS = {
    "admin": [
        "view_patient_directory",
        "view_patient_charts",
        "view_grounded_ai_summary",
        "view_care_gaps",
        "view_quality_alerts",
        "view_source_metadata",
        "view_patient_chat",
        "upload_fhir_bundle",
        "import_external_fhir",
        "investigate_ingestion",
        "view_audit_logs",
        "view_pipeline_runs",
        "record_dbt_transformation_audit",
        "view_demo_users",
    ],
    "clinician": [
        "view_patient_directory",
        "view_patient_charts",
        "view_grounded_ai_summary",
        "view_patient_chat",
        "view_demo_users",
    ],
    "care_coordinator": [
        "view_patient_directory",
        "view_patient_charts",
        "view_care_gaps",
        "view_patient_chat",
        "view_demo_users",
    ],
    "data_reviewer": [
        "view_patient_directory",
        "view_patient_charts",
        "view_quality_alerts",
        "view_source_metadata",
        "view_patient_chat",
        "upload_fhir_bundle",
        "import_external_fhir",
        "investigate_ingestion",
        "view_audit_logs",
        "view_pipeline_runs",
        "record_dbt_transformation_audit",
        "view_demo_users",
    ],
}


def permissions_for_role(role: str):
    return list(ROLE_PERMISSIONS.get(role, []))
