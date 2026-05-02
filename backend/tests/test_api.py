import json
from pathlib import Path

from app.core.database import SessionLocal
from app.models.curated_record_source import CuratedRecordSource
from app.models.ingestion_batch import IngestionBatch
from app.models.patient_source_identifier import PatientSourceIdentifier
from app.models.source_system import SourceSystem


SAMPLE_BUNDLE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "patient_bundle_1.json"


def load_sample_bundle():
    return json.loads(SAMPLE_BUNDLE_PATH.read_text(encoding="utf-8"))


def update_patient_reference(bundle, patient_id):
    for entry in bundle["entry"]:
        resource = entry["resource"]
        if resource["resourceType"] in {"Condition", "Observation", "Encounter", "MedicationRequest"}:
            resource["subject"]["reference"] = f"Patient/{patient_id}"
        elif resource["resourceType"] == "AllergyIntolerance":
            resource["patient"]["reference"] = f"Patient/{patient_id}"


def test_upload_bundle_creates_patient_record(client):
    bundle = load_sample_bundle()

    response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")}
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["import_mode"] == "created"
    assert payload["resource_counts"] == {
        "Patient": 1,
        "Condition": 2,
        "Observation": 2,
        "Encounter": 1,
        "MedicationRequest": 1,
        "AllergyIntolerance": 1
    }

    patient_response = client.get(f"/api/patients/{payload['patient_id']}")
    assert patient_response.status_code == 200

    patient_payload = patient_response.json()
    assert patient_payload["full_name"] == "John Doe"
    assert len(patient_payload["conditions"]) == 2
    assert len(patient_payload["observations"]) == 2
    assert len(patient_payload["encounters"]) == 1
    assert len(patient_payload["medication_requests"]) == 1
    assert len(patient_payload["allergies"]) == 1


def test_upload_bundle_is_idempotent_for_same_fhir_patient(client):
    bundle = load_sample_bundle()

    first_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")}
    )
    assert first_response.status_code == 200
    first_payload = first_response.json()

    bundle["entry"][0]["resource"]["name"][0]["given"] = ["Jane"]
    bundle["entry"] = bundle["entry"][:-1]

    second_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")}
    )
    assert second_response.status_code == 200
    second_payload = second_response.json()

    assert second_payload["patient_id"] == first_payload["patient_id"]
    assert second_payload["import_mode"] == "updated"

    patient_response = client.get(f"/api/patients/{first_payload['patient_id']}")
    patient_payload = patient_response.json()

    assert patient_payload["full_name"] == "Jane Doe"
    assert len(patient_payload["conditions"]) == 2
    assert len(patient_payload["observations"]) == 2
    assert len(patient_payload["encounters"]) == 1
    assert len(patient_payload["medication_requests"]) == 1
    assert len(patient_payload["allergies"]) == 0


def test_upload_bundle_records_multisource_ingestion_metadata(client):
    bundle = load_sample_bundle()

    response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")}
    )
    assert response.status_code == 200
    payload = response.json()

    db = SessionLocal()
    try:
        source_system = db.query(SourceSystem).filter(SourceSystem.name == "ClinSight FHIR Upload").one()
        ingestion_batch = db.query(IngestionBatch).one()
        patient_identifier = db.query(PatientSourceIdentifier).one()
        curated_sources = db.query(CuratedRecordSource).all()

        assert source_system.system_type == "fhir_upload"
        assert ingestion_batch.source_system_id == source_system.id
        assert ingestion_batch.filename == "patient_bundle_1.json"
        assert ingestion_batch.status == "processed"
        assert ingestion_batch.record_count == sum(payload["resource_counts"].values())
        assert patient_identifier.patient_id == payload["patient_id"]
        assert patient_identifier.identifier_type == "fhir_patient_id"
        assert patient_identifier.identifier_value == "patient-001"
        assert len(curated_sources) == sum(payload["resource_counts"].values())
        assert {source.curated_table_name for source in curated_sources} == {
            "patients",
            "conditions",
            "observations",
            "encounters",
            "medication_requests",
            "allergy_intolerances",
        }
    finally:
        db.close()


def test_list_patients_supports_search(client):
    first_bundle = load_sample_bundle()
    second_bundle = load_sample_bundle()

    first_bundle["entry"][0]["resource"]["id"] = "patient-001"
    first_bundle["entry"][0]["resource"]["name"][0]["given"] = ["John"]
    first_bundle["entry"][0]["resource"]["name"][0]["family"] = "Doe"
    update_patient_reference(first_bundle, "patient-001")

    second_bundle["entry"][0]["resource"]["id"] = "patient-002"
    second_bundle["entry"][0]["resource"]["name"][0]["given"] = ["Alice"]
    second_bundle["entry"][0]["resource"]["name"][0]["family"] = "Smith"
    update_patient_reference(second_bundle, "patient-002")

    client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(first_bundle), "application/json")}
    )
    client.post(
        "/api/upload",
        files={"file": ("patient_bundle_2.json", json.dumps(second_bundle), "application/json")}
    )

    response = client.get("/api/patients", params={"search": "Alice", "limit": 10, "offset": 0})

    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["full_name"] == "Alice Smith"


def test_quality_alerts_surface_structured_rules(client):
    bundle = load_sample_bundle()
    bundle["entry"][0]["resource"].pop("gender", None)
    bundle["entry"][4]["resource"].pop("valueQuantity", None)

    upload_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")}
    )
    patient_id = upload_response.json()["patient_id"]

    response = client.get(f"/api/patients/{patient_id}/quality-alerts")

    assert response.status_code == 200
    payload = response.json()

    assert payload["patient_id"] == patient_id
    assert any(alert["code"] == "missing_patient_gender" for alert in payload["alerts"])
    assert any(alert["code"] == "missing_observation_value" for alert in payload["alerts"])


def test_ai_insights_endpoint_returns_cited_report(client):
    bundle = load_sample_bundle()

    upload_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")}
    )
    patient_id = upload_response.json()["patient_id"]

    response = client.get(f"/api/patients/{patient_id}/ai-insights")

    assert response.status_code == 200
    payload = response.json()
    citation_ids = {citation["id"] for citation in payload["citations"]}

    assert payload["patient_id"] == patient_id
    assert payload["generated_by"] == "ClinSight grounded insight rules v1"
    assert payload["summary_sections"]
    assert payload["care_gaps"]
    assert payload["evaluation"]["unsupported_claims"] == 0
    assert payload["evaluation"]["unresolved_citations"] == 0
    assert all(
        citation_id in citation_ids
        for section in payload["summary_sections"]
        for claim in section["claims"]
        for citation_id in claim["citation_ids"]
    )


def test_demo_users_endpoint_returns_interview_roles(client):
    response = client.get("/api/demo-users")

    assert response.status_code == 200
    payload = response.json()

    assert len(payload["users"]) == 3
    assert {user["id"] for user in payload["users"]} == {"cmio", "nurse", "data_lead"}
    assert all(user["permissions"] for user in payload["users"])
