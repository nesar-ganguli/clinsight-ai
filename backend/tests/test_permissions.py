import pytest

from app.core.database import SessionLocal
from app.models.user import User


EXPECTED_PERMISSIONS = {
    "admin": {
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
    },
    "clinician": {
        "view_patient_directory",
        "view_patient_charts",
        "view_grounded_ai_summary",
        "view_patient_chat",
        "view_demo_users",
    },
    "care": {
        "view_patient_directory",
        "view_patient_charts",
        "view_care_gaps",
        "view_patient_chat",
        "view_demo_users",
    },
    "reviewer": {
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
    },
}


@pytest.mark.parametrize("username", ["admin", "clinician", "care", "reviewer"])
def test_login_and_current_user_return_complete_role_permissions(client, username):
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "clinsight-demo"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert set(login_payload["user"]["permissions"]) == EXPECTED_PERMISSIONS[username]

    current_user_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {login_payload['access_token']}"},
    )
    assert current_user_response.status_code == 200
    assert current_user_response.json()["permissions"] == login_payload["user"]["permissions"]


def test_demo_account_discovery_uses_current_database_names_and_active_state(client):
    initial_response = client.get("/api/auth/demo-accounts")
    assert initial_response.status_code == 200

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").one()
        reviewer = db.query(User).filter(User.username == "reviewer").one()
        admin.full_name = "Jordan Database Admin"
        reviewer.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.get("/api/auth/demo-accounts")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["username"] for item in items] == ["admin", "clinician", "care"]
    assert items[0]["full_name"] == "Jordan Database Admin"
    assert set(items[0]["permissions"]) == EXPECTED_PERMISSIONS["admin"]
