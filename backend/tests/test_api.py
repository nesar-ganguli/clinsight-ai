import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.allergy_intolerance import AllergyIntolerance
from app.models.condition import Condition
from app.models.curated_record_source import CuratedRecordSource
from app.models.encounter import Encounter
from app.models.ingestion_batch import IngestionBatch
from app.models.medication_request import MedicationRequest
from app.models.observation import Observation
from app.models.patient import Patient
from app.models.patient_source_identifier import PatientSourceIdentifier
from app.models.source_system import SourceSystem
from app.services import ingestion as ingestion_service


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


def find_resource(bundle, resource_type, resource_id):
    return next(
        entry["resource"]
        for entry in bundle["entry"]
        if entry["resource"].get("resourceType") == resource_type
        and entry["resource"].get("id") == resource_id
    )


def mark_as_smart_health_it_bundle(bundle):
    bundle["meta"] = {
        "source": "smart-health-it-r4-sandbox",
        "tag": [
            {
                "system": "https://clinsight.ai/source-type",
                "code": "smart-health-it-r4-sandbox",
                "display": "SMART Health IT R4 Sandbox",
            }
        ],
    }


def auth_headers(client, username="admin"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "clinsight-demo"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_upload_bundle_creates_patient_record(client):
    bundle = load_sample_bundle()

    response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
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

    patient_response = client.get(f"/api/patients/{payload['patient_id']}", headers=auth_headers(client, "clinician"))
    assert patient_response.status_code == 200

    patient_payload = patient_response.json()
    assert patient_payload["full_name"] == "John Doe"
    assert len(patient_payload["conditions"]) == 2
    assert len(patient_payload["observations"]) == 2
    assert len(patient_payload["encounters"]) == 1
    assert len(patient_payload["medication_requests"]) == 1
    assert len(patient_payload["allergies"]) == 1


def test_uploading_same_bundle_twice_upserts_without_duplicates(client):
    bundle = load_sample_bundle()

    first_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    assert first_response.status_code == 200
    first_payload = first_response.json()

    db = SessionLocal()
    try:
        first_record_ids = {
            "conditions": [record.id for record in db.query(Condition).order_by(Condition.id)],
            "observations": [record.id for record in db.query(Observation).order_by(Observation.id)],
            "encounters": [record.id for record in db.query(Encounter).order_by(Encounter.id)],
            "medications": [record.id for record in db.query(MedicationRequest).order_by(MedicationRequest.id)],
            "allergies": [record.id for record in db.query(AllergyIntolerance).order_by(AllergyIntolerance.id)],
        }
    finally:
        db.close()

    second_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    assert second_response.status_code == 200
    second_payload = second_response.json()

    assert second_payload["patient_id"] == first_payload["patient_id"]
    assert second_payload["import_mode"] == "updated"

    db = SessionLocal()
    try:
        second_record_ids = {
            "conditions": [record.id for record in db.query(Condition).order_by(Condition.id)],
            "observations": [record.id for record in db.query(Observation).order_by(Observation.id)],
            "encounters": [record.id for record in db.query(Encounter).order_by(Encounter.id)],
            "medications": [record.id for record in db.query(MedicationRequest).order_by(MedicationRequest.id)],
            "allergies": [record.id for record in db.query(AllergyIntolerance).order_by(AllergyIntolerance.id)],
        }
        assert second_record_ids == first_record_ids
        assert db.query(CuratedRecordSource).count() == sum(second_payload["resource_counts"].values())
        assert db.query(IngestionBatch).count() == 2
        assert db.query(Patient).count() == 1
        assert db.query(PatientSourceIdentifier).count() == 1
        latest_batch = db.query(IngestionBatch).order_by(IngestionBatch.id.desc()).first()
        assert {
            source.ingestion_batch_id
            for source in db.query(CuratedRecordSource).all()
        } == {latest_batch.id}
    finally:
        db.close()


def test_same_source_updates_records_and_retains_omitted_resources(client):
    bundle = load_sample_bundle()

    first_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    assert first_response.status_code == 200
    patient_id = first_response.json()["patient_id"]

    bundle["entry"][0]["resource"]["name"][0]["given"] = ["Jane"]
    condition = find_resource(bundle, "Condition", "condition-001")
    condition["code"]["coding"][0]["display"] = "Updated hypertension"
    condition["clinicalStatus"]["coding"][0]["code"] = "resolved"
    observation = find_resource(bundle, "Observation", "observation-001")
    observation["valueString"] = "142/88"
    bundle["entry"] = [
        entry
        for entry in bundle["entry"]
        if entry["resource"].get("resourceType") != "AllergyIntolerance"
    ]

    second_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    assert second_response.status_code == 200
    assert second_response.json()["patient_id"] == patient_id

    patient_response = client.get(f"/api/patients/{patient_id}", headers=auth_headers(client, "clinician"))
    assert patient_response.status_code == 200
    patient_payload = patient_response.json()

    assert patient_payload["full_name"] == "Jane Doe"
    assert len(patient_payload["conditions"]) == 2
    assert len(patient_payload["observations"]) == 2
    assert len(patient_payload["encounters"]) == 1
    assert len(patient_payload["medication_requests"]) == 1
    assert len(patient_payload["allergies"]) == 1
    updated_condition = next(
        item for item in patient_payload["conditions"] if item["fhir_condition_id"] == "condition-001"
    )
    updated_observation = next(
        item for item in patient_payload["observations"] if item["fhir_observation_id"] == "observation-001"
    )
    assert updated_condition["condition_name"] == "Updated hypertension"
    assert updated_condition["clinical_status"] == "resolved"
    assert updated_observation["value"] == "142/88"


def test_identical_patient_ids_from_different_sources_create_separate_canonical_patients(client):
    upload_bundle = load_sample_bundle()
    smart_bundle = load_sample_bundle()
    mark_as_smart_health_it_bundle(smart_bundle)

    upload_condition = find_resource(upload_bundle, "Condition", "condition-001")
    upload_condition["code"]["coding"][0]["display"] = "Upload hypertension"
    smart_condition = find_resource(smart_bundle, "Condition", "condition-001")
    smart_condition["code"]["coding"][0]["display"] = "SMART hypertension"

    upload_response = client.post(
        "/api/upload",
        files={"file": ("upload.json", json.dumps(upload_bundle), "application/json")},
        headers=auth_headers(client),
    )
    assert upload_response.status_code == 200

    smart_response = client.post(
        "/api/upload",
        files={"file": ("smart.json", json.dumps(smart_bundle), "application/json")},
        headers=auth_headers(client),
    )
    assert smart_response.status_code == 200
    assert smart_response.json()["patient_id"] != upload_response.json()["patient_id"]
    assert smart_response.json()["import_mode"] == "created"

    upload_patient_response = client.get(
        f"/api/patients/{upload_response.json()['patient_id']}",
        headers=auth_headers(client, "clinician"),
    )
    smart_patient_response = client.get(
        f"/api/patients/{smart_response.json()['patient_id']}",
        headers=auth_headers(client, "clinician"),
    )
    assert upload_patient_response.status_code == 200
    assert smart_patient_response.status_code == 200
    upload_patient = upload_patient_response.json()
    smart_patient = smart_patient_response.json()
    assert len(upload_patient["conditions"]) == 2
    assert len(smart_patient["conditions"]) == 2
    assert {item["source_system"] for item in upload_patient["conditions"]} == {
        "ClinSight FHIR Upload"
    }
    assert {item["source_system"] for item in smart_patient["conditions"]} == {
        "SMART Health IT R4 Sandbox"
    }
    assert find_resource(upload_bundle, "Condition", "condition-001")["code"]["coding"][0]["display"] == (
        next(item for item in upload_patient["conditions"] if item["fhir_condition_id"] == "condition-001")[
            "condition_name"
        ]
    )
    assert find_resource(smart_bundle, "Condition", "condition-001")["code"]["coding"][0]["display"] == (
        next(item for item in smart_patient["conditions"] if item["fhir_condition_id"] == "condition-001")[
            "condition_name"
        ]
    )

    db = SessionLocal()
    try:
        identifiers = db.query(PatientSourceIdentifier).order_by(PatientSourceIdentifier.id).all()
        assert db.query(Patient).count() == 2
        assert len(identifiers) == 2
        assert {identifier.identifier_value for identifier in identifiers} == {"patient-001"}
        assert len({identifier.source_system_id for identifier in identifiers}) == 2
        assert len({identifier.patient_id for identifier in identifiers}) == 2
    finally:
        db.close()


def test_manually_mapped_source_identifiers_resolve_to_one_canonical_patient(client):
    upload_bundle = load_sample_bundle()
    smart_bundle = load_sample_bundle()
    smart_patient = find_resource(smart_bundle, "Patient", "patient-001")
    smart_patient["id"] = "smart-linked-001"
    smart_patient["name"][0]["given"] = ["Jonathan"]
    update_patient_reference(smart_bundle, "smart-linked-001")
    mark_as_smart_health_it_bundle(smart_bundle)

    upload_response = client.post(
        "/api/upload",
        files={"file": ("upload.json", json.dumps(upload_bundle), "application/json")},
        headers=auth_headers(client),
    )
    assert upload_response.status_code == 200
    canonical_patient_id = upload_response.json()["patient_id"]

    db = SessionLocal()
    try:
        smart_source = SourceSystem(
            name="SMART Health IT R4 Sandbox",
            system_type="external_fhir_api",
            facility_name="SMART Health IT public sandbox",
            external_system_id="smart-health-it-r4-sandbox",
            is_active=True,
        )
        db.add(smart_source)
        db.flush()
        db.add(
            PatientSourceIdentifier(
                patient_id=canonical_patient_id,
                source_system_id=smart_source.id,
                identifier_type="fhir_patient_id",
                identifier_value="smart-linked-001",
                assigning_authority="Manual identity mapping",
            )
        )
        db.commit()
    finally:
        db.close()

    smart_response = client.post(
        "/api/upload",
        files={"file": ("smart.json", json.dumps(smart_bundle), "application/json")},
        headers=auth_headers(client),
    )
    assert smart_response.status_code == 200
    assert smart_response.json()["patient_id"] == canonical_patient_id
    assert smart_response.json()["import_mode"] == "updated"

    patient_response = client.get(
        f"/api/patients/{canonical_patient_id}",
        headers=auth_headers(client, "clinician"),
    )
    assert patient_response.status_code == 200
    patient_payload = patient_response.json()
    assert patient_payload["full_name"] == "Jonathan Doe"
    assert patient_payload["fhir_patient_id"] == "patient-001"
    assert len(patient_payload["conditions"]) == 4
    assert {item["source_system"] for item in patient_payload["conditions"]} == {
        "ClinSight FHIR Upload",
        "SMART Health IT R4 Sandbox",
    }

    db = SessionLocal()
    try:
        identifiers = (
            db.query(PatientSourceIdentifier)
            .filter(PatientSourceIdentifier.patient_id == canonical_patient_id)
            .order_by(PatientSourceIdentifier.id)
            .all()
        )
        assert db.query(Patient).count() == 1
        assert len(identifiers) == 2
        assert {identifier.identifier_value for identifier in identifiers} == {
            "patient-001",
            "smart-linked-001",
        }
        assert len({identifier.source_system_id for identifier in identifiers}) == 2
    finally:
        db.close()


def test_upload_bundle_records_multisource_ingestion_metadata(client):
    bundle = load_sample_bundle()

    response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
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
        assert ingestion_batch.ingestion_type == "fhir_upload"
        assert ingestion_batch.filename == "patient_bundle_1.json"
        assert ingestion_batch.status == "success"
        assert ingestion_batch.record_count == sum(payload["resource_counts"].values())
        assert ingestion_batch.accepted_count == ingestion_batch.record_count
        assert ingestion_batch.rejected_count == 0
        assert ingestion_batch.error_message is None
        assert ingestion_batch.started_at is not None
        assert ingestion_batch.completed_at is not None
        assert patient_identifier.patient_id == payload["patient_id"]
        assert patient_identifier.identifier_type == "fhir_patient_id"
        assert patient_identifier.identifier_value == "patient-001"
        assert len(curated_sources) == sum(payload["resource_counts"].values())
        patient = db.query(Patient).filter(Patient.id == payload["patient_id"]).one()
        assert patient.source_type == "fhir_upload"
        assert patient.source_system == "ClinSight FHIR Upload"
        assert patient.source_record_id == "patient-001"
        assert patient.ingestion_batch_id == str(ingestion_batch.id)
        assert patient.transformed_at is not None
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


def test_failed_ingestion_batch_persists_when_bundle_has_no_patient(client):
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-without-patient",
                }
            }
        ],
    }

    response = client.post(
        "/api/upload",
        files={"file": ("missing-patient.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No Patient resource found in bundle"

    db = SessionLocal()
    try:
        ingestion_batch = db.query(IngestionBatch).one()
        assert ingestion_batch.status == "failed"
        assert ingestion_batch.record_count == 1
        assert ingestion_batch.accepted_count == 0
        assert ingestion_batch.rejected_count == 1
        assert ingestion_batch.error_message == "No Patient resource found in bundle"
        assert ingestion_batch.started_at is not None
        assert ingestion_batch.completed_at is not None
        assert db.query(Patient).count() == 0
        assert db.query(CuratedRecordSource).count() == 0
    finally:
        db.close()


def test_clinical_records_roll_back_while_failed_batch_and_sanitized_error_persist(
    client,
    monkeypatch,
):
    bundle = load_sample_bundle()
    original_upsert = ingestion_service._upsert_clinical_record
    sensitive_error = "patient Jane Doe payload {\"ssn\":\"123-45-6789\"}"

    def fail_after_clinical_write(*args, **kwargs):
        original_upsert(*args, **kwargs)
        raise ValueError(sensitive_error)

    monkeypatch.setattr(
        ingestion_service,
        "_upsert_clinical_record",
        fail_after_clinical_write,
    )

    response = client.post(
        "/api/upload",
        files={"file": ("rollback.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )

    assert response.status_code == 400

    db = SessionLocal()
    try:
        ingestion_batch = db.query(IngestionBatch).one()
        assert ingestion_batch.status == "failed"
        assert ingestion_batch.accepted_count == 0
        assert ingestion_batch.rejected_count == ingestion_batch.record_count
        assert ingestion_batch.error_message == "ValueError: FHIR bundle ingestion failed"
        assert "Jane Doe" not in ingestion_batch.error_message
        assert "123-45-6789" not in ingestion_batch.error_message
        assert ingestion_batch.completed_at is not None

        assert db.query(SourceSystem).count() == 1
        assert db.query(Patient).count() == 0
        assert db.query(PatientSourceIdentifier).count() == 0
        assert db.query(Condition).count() == 0
        assert db.query(CuratedRecordSource).count() == 0
    finally:
        db.close()


def test_upload_serializes_typed_clinical_dates_as_iso_values(client):
    bundle = load_sample_bundle()
    find_resource(bundle, "Condition", "condition-001")["onsetDateTime"] = "2026-04-01"
    find_resource(bundle, "Observation", "observation-001")["effectiveDateTime"] = (
        "2026-04-01T14:30:00Z"
    )
    encounter = find_resource(bundle, "Encounter", "encounter-001")
    encounter["period"]["start"] = "2026-04-01T10:30:00-04:00"
    encounter["period"]["end"] = None
    find_resource(bundle, "MedicationRequest", "medicationrequest-001")["authoredOn"] = None
    find_resource(bundle, "AllergyIntolerance", "allergy-001")["recordedDate"] = "invalid-date"

    upload_response = client.post(
        "/api/upload",
        files={"file": ("typed-dates.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    assert upload_response.status_code == 200

    patient_response = client.get(
        f"/api/patients/{upload_response.json()['patient_id']}",
        headers=auth_headers(client, "clinician"),
    )
    assert patient_response.status_code == 200
    patient = patient_response.json()

    condition = next(item for item in patient["conditions"] if item["fhir_condition_id"] == "condition-001")
    observation = next(
        item for item in patient["observations"] if item["fhir_observation_id"] == "observation-001"
    )
    stored_encounter = patient["encounters"][0]

    assert condition["onset_date"] == "2026-04-01T00:00:00Z"
    assert observation["effective_date"] == "2026-04-01T14:30:00Z"
    assert stored_encounter["period_start"] == "2026-04-01T14:30:00Z"
    assert stored_encounter["period_end"] is None
    assert patient["medication_requests"][0]["authored_on"] is None
    assert patient["allergies"][0]["recorded_date"] is None

    db = SessionLocal()
    try:
        assert isinstance(db.query(Condition).filter(Condition.id == condition["id"]).one().onset_date, datetime)
        assert isinstance(
            db.query(Observation).filter(Observation.id == observation["id"]).one().effective_date,
            datetime,
        )
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
        files={"file": ("patient_bundle_1.json", json.dumps(first_bundle), "application/json")},
        headers=auth_headers(client),
    )
    client.post(
        "/api/upload",
        files={"file": ("patient_bundle_2.json", json.dumps(second_bundle), "application/json")},
        headers=auth_headers(client),
    )

    response = client.get(
        "/api/patients",
        params={"search": "Alice", "limit": 10, "offset": 0},
        headers=auth_headers(client, "clinician"),
    )

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
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    patient_id = upload_response.json()["patient_id"]

    response = client.get(f"/api/patients/{patient_id}/quality-alerts", headers=auth_headers(client, "reviewer"))

    assert response.status_code == 200
    payload = response.json()

    assert payload["patient_id"] == patient_id
    assert any(alert["code"] == "missing_patient_gender" for alert in payload["alerts"])
    assert any(alert["code"] == "missing_observation_value" for alert in payload["alerts"])


def test_ai_insights_endpoint_returns_cited_report(client):
    bundle = load_sample_bundle()

    upload_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    patient_id = upload_response.json()["patient_id"]

    response = client.get(f"/api/patients/{patient_id}/ai-insights", headers=auth_headers(client, "clinician"))

    assert response.status_code == 200
    payload = response.json()
    citation_ids = {citation["id"] for citation in payload["citations"]}

    assert payload["patient_id"] == patient_id
    assert payload["generated_by"] == "ClinSight grounded insight rules v1"
    assert payload["summary_sections"]
    assert payload["care_gaps"]
    assert all(citation["source_system"] == "ClinSight FHIR Upload" for citation in payload["citations"])
    assert all(citation["ingestion_batch_id"] is not None for citation in payload["citations"])
    assert payload["evaluation"]["unsupported_claims"] == 0
    assert payload["evaluation"]["unresolved_citations"] == 0
    assert all(
        citation_id in citation_ids
        for section in payload["summary_sections"]
        for claim in section["claims"]
        for citation_id in claim["citation_ids"]
    )
    db = SessionLocal()
    try:
        insight_audit = (
            db.query(AuditLog)
            .filter(AuditLog.patient_id == patient_id, AuditLog.action == "ai_insight_report_viewed")
            .one()
        )
        assert insight_audit.resource_type == "patient"
        assert insight_audit.resource_id == str(patient_id)
        assert insight_audit.event_metadata["citation_count"] == len(payload["citations"])
    finally:
        db.close()


def test_patient_chat_answers_with_grounded_citations_and_audit(client):
    bundle = load_sample_bundle()
    upload_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    patient_id = upload_response.json()["patient_id"]

    response = client.post(
        f"/api/patients/{patient_id}/chat",
        json={"question": "Has this patient had an A1c recently?"},
        headers=auth_headers(client, "clinician"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["patient_id"] == patient_id
    assert payload["llm_used"] is False
    assert payload["citations"]
    assert "diabetes_a1c" in payload["retrieval_strategy"]
    assert any(citation["resource_type"] == "Observation" for citation in payload["citations"])

    db = SessionLocal()
    try:
        chat_audit = (
            db.query(AuditLog)
            .filter(AuditLog.patient_id == patient_id, AuditLog.action == "patient_chat_question_asked")
            .one()
        )
        assert chat_audit.resource_type == "patient"
        assert chat_audit.event_metadata["question"] == "Has this patient had an A1c recently?"
        assert chat_audit.event_metadata["citation_count"] == len(payload["citations"])
    finally:
        db.close()


def test_patient_chat_refuses_treatment_advice(client):
    bundle = load_sample_bundle()
    upload_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    patient_id = upload_response.json()["patient_id"]

    response = client.post(
        f"/api/patients/{patient_id}/chat",
        json={"question": "What medication should I prescribe for this patient?"},
        headers=auth_headers(client, "clinician"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["refused"] is True
    assert "cannot provide diagnosis or treatment recommendations" in payload["answer"]


def test_patient_chat_uses_github_models_when_configured(client, monkeypatch):
    bundle = load_sample_bundle()
    upload_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    patient_id = upload_response.json()["patient_id"]

    class FakeGithubResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "answer": "The available records include a documented A1c-related observation.",
                                    "confidence": "high",
                                    "citation_ids": ["Observation:1"],
                                    "safety_notes": ["Grounded to retrieved evidence."],
                                }
                            )
                        }
                    }
                ]
            }

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeGithubResponse()

    monkeypatch.setattr("app.services.patient_chat.settings.llm_provider", "github")
    monkeypatch.setattr("app.services.patient_chat.settings.github_models_token", "ghp_test")
    monkeypatch.setattr("app.services.patient_chat.settings.github_models_model", "openai/gpt-4o-mini")
    monkeypatch.setattr("app.services.patient_chat.httpx.post", fake_post)

    response = client.post(
        f"/api/patients/{patient_id}/chat",
        json={"question": "Has this patient had an A1c recently?"},
        headers=auth_headers(client, "clinician"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_used"] is True
    assert payload["generated_by"].startswith("GitHub Models openai/gpt-4o-mini")
    assert captured["url"] == "https://models.github.ai/inference/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer ghp_test"
    assert captured["json"]["model"] == "openai/gpt-4o-mini"
    assert captured["json"]["response_format"]["type"] == "json_schema"


def test_dbt_curated_patient_surfaces_in_api_quality_and_insights(client):
    db = SessionLocal()
    try:
        create_test_clinical_tables(db)
        seed_test_clinical_patient(db)

        list_response = client.get(
            "/api/patients",
            params={"search": "Morgan", "limit": 10, "offset": 0},
            headers=auth_headers(client, "clinician"),
        )
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert list_payload["total"] == 1
        assert list_payload["items"][0]["id"] == 900001
        assert list_payload["items"][0]["full_name"] == "Avery Morgan"

        detail_response = client.get("/api/patients/900001", headers=auth_headers(client, "clinician"))
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["full_name"] == "Avery Morgan"
        assert len(detail_payload["conditions"]) == 1
        assert len(detail_payload["observations"]) == 2
        assert len(detail_payload["encounters"]) == 1
        assert len(detail_payload["medication_requests"]) == 1
        assert len(detail_payload["allergies"]) == 1

        quality_response = client.get("/api/patients/900001/quality-alerts", headers=auth_headers(client, "reviewer"))
        assert quality_response.status_code == 200
        quality_payload = quality_response.json()
        assert quality_payload["patient_id"] == 900001
        assert quality_payload["alerts"] == []

        insights_response = client.get("/api/patients/900001/ai-insights", headers=auth_headers(client, "clinician"))
        assert insights_response.status_code == 200
        insights_payload = insights_response.json()
        assert insights_payload["patient_id"] == 900001
        assert insights_payload["summary_sections"]
        assert insights_payload["care_gaps"]
        assert all(citation["source_system"] == "internal_hospital_ods" for citation in insights_payload["citations"])
        assert all(citation["ingestion_batch_id"] == "test-batch-001" for citation in insights_payload["citations"])
        assert insights_payload["evaluation"]["unsupported_claims"] == 0
    finally:
        drop_test_clinical_tables(db)
        db.close()


def test_demo_users_endpoint_returns_interview_roles(client):
    response = client.get("/api/demo-users", headers=auth_headers(client))

    assert response.status_code == 200
    payload = response.json()

    assert len(payload["users"]) == 3
    assert {user["id"] for user in payload["users"]} == {"cmio", "nurse", "data_lead"}
    assert all(user["permissions"] for user in payload["users"])


def test_protected_endpoints_require_authentication(client):
    response = client.get("/api/patients")
    assert response.status_code == 401


def test_role_permissions_and_patient_access_audit(client):
    bundle = load_sample_bundle()

    upload_response = client.post(
        "/api/upload",
        files={"file": ("patient_bundle_1.json", json.dumps(bundle), "application/json")},
        headers=auth_headers(client),
    )
    patient_id = upload_response.json()["patient_id"]

    clinician_headers = auth_headers(client, "clinician")
    denied_quality = client.get(f"/api/patients/{patient_id}/quality-alerts", headers=clinician_headers)
    assert denied_quality.status_code == 403

    detail_response = client.get(f"/api/patients/{patient_id}", headers=clinician_headers)
    assert detail_response.status_code == 200

    db = SessionLocal()
    try:
        audit_log = (
            db.query(AuditLog)
            .filter(AuditLog.patient_id == patient_id, AuditLog.action == "patient_chart_access")
            .one()
        )
        assert audit_log.username == "clinician"
        assert audit_log.role == "clinician"
        assert audit_log.action == "patient_chart_access"
        assert audit_log.resource_type == "patient"
        assert audit_log.resource_id == str(patient_id)
        assert audit_log.event_metadata == {"patient_id": patient_id}
    finally:
        db.close()


def test_admin_can_view_audit_logs_and_dbt_events(client):
    admin_headers = auth_headers(client)
    dbt_response = client.post(
        "/api/audit-logs/dbt-transformation",
        json={
            "status": "completed",
            "invocation_id": "dbt-test-001",
            "selected_models": ["marts.clinical"],
            "metadata": {"row_count": 1000},
        },
        headers=admin_headers,
    )
    assert dbt_response.status_code == 200

    audit_response = client.get("/api/audit-logs", headers=admin_headers)

    assert audit_response.status_code == 200
    payload = audit_response.json()
    actions = {item["action"] for item in payload["items"]}
    assert "user_login" in actions
    assert "dbt_transformation_completed" in actions

    dbt_event = next(item for item in payload["items"] if item["action"] == "dbt_transformation_completed")
    assert dbt_event["resource_type"] == "dbt_transformation"
    assert dbt_event["resource_id"] == "dbt-test-001"
    assert dbt_event["metadata"]["selected_models"] == ["marts.clinical"]


def test_clinician_cannot_view_audit_logs(client):
    response = client.get("/api/audit-logs", headers=auth_headers(client, "clinician"))
    assert response.status_code == 403


def test_smart_health_it_patient_search_requires_data_reviewer_role(client, monkeypatch):
    def fake_search_smart_patients(search=None, count=10):
        return [
            {
                "id": "smart-patient-001",
                "full_name": "SMART Patient",
                "gender": "female",
                "birth_date": "1980-01-01",
            }
        ]

    monkeypatch.setattr("app.api.routes_external_fhir.search_smart_patients", fake_search_smart_patients)

    denied_response = client.get(
        "/api/external-fhir/smart/patients",
        headers=auth_headers(client, "clinician"),
    )
    assert denied_response.status_code == 403

    response = client.get(
        "/api/external-fhir/smart/patients",
        params={"search": "smart"},
        headers=auth_headers(client, "reviewer"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_system"] == "SMART Health IT R4 Sandbox"
    assert payload["items"][0]["id"] == "smart-patient-001"


def test_smart_health_it_import_reuses_fhir_ingestion_and_source_metadata(client, monkeypatch):
    bundle = load_sample_bundle()
    bundle["meta"] = {
        "source": "smart-health-it-r4-sandbox",
        "tag": [{"code": "smart-health-it-r4-sandbox"}],
    }
    bundle["entry"][0]["resource"]["id"] = "smart-patient-001"
    update_patient_reference(bundle, "smart-patient-001")

    monkeypatch.setattr("app.api.routes_external_fhir.fetch_smart_patient_bundle", lambda patient_id: bundle)

    response = client.post(
        "/api/external-fhir/smart/import/smart-patient-001",
        headers=auth_headers(client, "reviewer"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_system"] == "SMART Health IT R4 Sandbox"
    assert payload["external_patient_id"] == "smart-patient-001"
    assert payload["resource_counts"]["Patient"] == 1

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == payload["patient_id"]).one()
        source_system = db.query(SourceSystem).filter(SourceSystem.name == "SMART Health IT R4 Sandbox").one()
        import_audit = (
            db.query(AuditLog)
            .filter(AuditLog.action == "external_fhir_patient_imported")
            .one()
        )

        assert source_system.system_type == "external_fhir_api"
        assert patient.source_type == "external_fhir_api"
        assert patient.source_system == "SMART Health IT R4 Sandbox"
        assert patient.source_record_id == "smart-patient-001"
        assert import_audit.resource_id == str(payload["patient_id"])
        assert import_audit.event_metadata["external_patient_id"] == "smart-patient-001"
    finally:
        db.close()


def create_test_clinical_tables(db):
    drop_test_clinical_tables(db)
    db.execute(text("""
        create table clinical_patients (
            id integer primary key,
            fhir_patient_id text,
            full_name text,
            gender text,
            birth_date text,
            source_type text,
            source_system text,
            source_record_id text,
            ingestion_batch_id text,
            transformed_at text,
            source_patient_id text
        )
    """))
    db.execute(text("""
        create table clinical_conditions (
            id integer primary key,
            patient_id integer,
            fhir_condition_id text,
            condition_code text,
            condition_name text,
            clinical_status text,
            onset_date text,
            source_type text,
            source_system text,
            source_record_id text,
            ingestion_batch_id text,
            transformed_at text
        )
    """))
    db.execute(text("""
        create table clinical_observations (
            id integer primary key,
            patient_id integer,
            fhir_observation_id text,
            observation_code text,
            observation_name text,
            value text,
            unit text,
            effective_date text,
            source_type text,
            source_system text,
            source_record_id text,
            ingestion_batch_id text,
            transformed_at text
        )
    """))
    db.execute(text("""
        create table clinical_encounters (
            id integer primary key,
            patient_id integer,
            fhir_encounter_id text,
            status text,
            encounter_class text,
            encounter_type text,
            period_start text,
            period_end text,
            source_type text,
            source_system text,
            source_record_id text,
            ingestion_batch_id text,
            transformed_at text
        )
    """))
    db.execute(text("""
        create table clinical_medication_requests (
            id integer primary key,
            patient_id integer,
            fhir_medication_request_id text,
            status text,
            intent text,
            medication_code text,
            medication_name text,
            authored_on text,
            source_type text,
            source_system text,
            source_record_id text,
            ingestion_batch_id text,
            transformed_at text
        )
    """))
    db.execute(text("""
        create table clinical_allergies (
            id integer primary key,
            patient_id integer,
            fhir_allergy_id text,
            clinical_status text,
            verification_status text,
            allergy_code text,
            allergy_name text,
            criticality text,
            recorded_date text,
            source_type text,
            source_system text,
            source_record_id text,
            ingestion_batch_id text,
            transformed_at text
        )
    """))
    db.commit()


def seed_test_clinical_patient(db):
    db.execute(text("""
        insert into clinical_patients (
            id, fhir_patient_id, full_name, gender, birth_date, source_type, source_system,
            source_record_id, ingestion_batch_id, transformed_at, source_patient_id
        ) values (
            900001, null, 'Avery Morgan', 'female', '1978-04-12', 'hospital_database',
            'internal_hospital_ods', 'MRN900001', 'test-batch-001', '2026-05-02T21:00:00', 'MRN900001'
        )
    """))
    db.execute(text("""
        insert into clinical_conditions (
            id, patient_id, fhir_condition_id, condition_code, condition_name, clinical_status, onset_date,
            source_type, source_system, source_record_id, ingestion_batch_id, transformed_at
        ) values (
            910001, 900001, null, 'E11.9', 'Type 2 Diabetes Mellitus Without Complications', 'active',
            '2026-01-01', 'hospital_database', 'internal_hospital_ods', 'DX900001', 'test-batch-001',
            '2026-05-02T21:00:00'
        )
    """))
    db.execute(text("""
        insert into clinical_observations (
            id, patient_id, fhir_observation_id, observation_code, observation_name, value, unit, effective_date,
            source_type, source_system, source_record_id, ingestion_batch_id, transformed_at
        ) values
            (920001, 900001, null, '4548-4', 'Hemoglobin A1c', '8.2', '%', '2026-04-01T14:00:00',
                'hospital_database', 'internal_hospital_ods', 'LAB900001', 'test-batch-001', '2026-05-02T21:00:00'),
            (920002, 900001, null, '2345-7', 'Glucose', '140', 'mg/dL', '2026-04-01T14:00:00',
                'hospital_database', 'internal_hospital_ods', 'LAB900002', 'test-batch-001', '2026-05-02T21:00:00')
    """))
    db.execute(text("""
        insert into clinical_encounters (
            id, patient_id, fhir_encounter_id, status, encounter_class, encounter_type, period_start, period_end,
            source_type, source_system, source_record_id, ingestion_batch_id, transformed_at
        ) values (
            930001, 900001, null, 'finished', 'hospital', 'office_visit', '2026-04-01T08:00:00',
            '2026-04-01T16:00:00', 'hospital_database', 'internal_hospital_ods', 'ENC900001',
            'test-batch-001', '2026-05-02T21:00:00'
        )
    """))
    db.execute(text("""
        insert into clinical_medication_requests (
            id, patient_id, fhir_medication_request_id, status, intent, medication_code, medication_name, authored_on,
            source_type, source_system, source_record_id, ingestion_batch_id, transformed_at
        ) values (
            940001, 900001, null, 'active', 'order', 'RXN-860975', 'Metformin 500 Mg Oral Tablet',
            '2026-04-01T11:00:00', 'hospital_database', 'internal_hospital_ods', 'MED900001',
            'test-batch-001', '2026-05-02T21:00:00'
        )
    """))
    db.execute(text("""
        insert into clinical_allergies (
            id, patient_id, fhir_allergy_id, clinical_status, verification_status, allergy_code, allergy_name,
            criticality, recorded_date, source_type, source_system, source_record_id, ingestion_batch_id, transformed_at
        ) values (
            950001, 900001, null, 'active', 'confirmed', '7980', 'Penicillin', 'high', '2026-04-01T10:00:00',
            'hospital_database', 'internal_hospital_ods', 'ALG900001', 'test-batch-001', '2026-05-02T21:00:00'
        )
    """))
    db.commit()


def drop_test_clinical_tables(db):
    for table_name in [
        "clinical_allergies",
        "clinical_medication_requests",
        "clinical_observations",
        "clinical_conditions",
        "clinical_encounters",
        "clinical_patients",
    ]:
        db.execute(text(f"drop table if exists {table_name}"))
    db.commit()
