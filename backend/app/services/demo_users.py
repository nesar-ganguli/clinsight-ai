from typing import Any, Dict, List


DEMO_USERS: List[Dict[str, Any]] = [
    {
        "id": "cmio",
        "name": "Dr. Maya Chen",
        "role": "CMIO reviewer",
        "focus": "Reviews summary credibility, safety posture, and alert usefulness.",
        "permissions": [
            "view_patient_directory",
            "view_grounded_ai_summary",
            "view_quality_alerts",
            "view_metrics",
        ],
    },
    {
        "id": "nurse",
        "name": "Alex Rivera",
        "role": "Care coordinator",
        "focus": "Uses care gap suggestions and chart inconsistencies to prepare follow-up.",
        "permissions": [
            "view_patient_directory",
            "view_care_gaps",
            "upload_fhir_bundle",
        ],
    },
    {
        "id": "data_lead",
        "name": "Sam Patel",
        "role": "Clinical data lead",
        "focus": "Evaluates ingestion quality, source coverage, and repeatable demo metrics.",
        "permissions": [
            "upload_fhir_bundle",
            "view_source_citations",
            "run_demo_metrics",
        ],
    },
]


def list_demo_users() -> List[Dict[str, Any]]:
    return DEMO_USERS
