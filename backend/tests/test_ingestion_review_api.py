from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.ingestion_batch import IngestionBatch
from app.models.quarantine_record import QuarantineRecord
from app.models.source_system import SourceSystem


def auth_headers(client, username="admin"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "clinsight-demo"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_quarantined_batch():
    db = SessionLocal()
    try:
        source = SourceSystem(name="FHIR Upload", system_type="fhir_r4")
        db.add(source)
        db.flush()
        batch = IngestionBatch(
            source_system_id=source.id,
            ingestion_type="fhir_bundle_upload",
            filename="mixed-validation-errors.json",
            status="completed_with_rejections",
            record_count=2,
            accepted_count=1,
            rejected_count=1,
        )
        db.add(batch)
        db.flush()
        record = QuarantineRecord(
            ingestion_batch_id=batch.id,
            source_system_id=source.id,
            resource_type="Observation",
            source_record_id="observation-bad-date",
            error_code="invalid_effective_date",
            error_message="Observation effectiveDateTime is not a valid date.",
            raw_payload={
                "resourceType": "Observation",
                "id": "observation-bad-date",
                "effectiveDateTime": "not-a-date",
            },
        )
        db.add(record)
        db.commit()
        return batch.id, record.id
    finally:
        db.close()


def test_admin_can_list_batches_and_quarantine_metadata_without_raw_payload(client):
    batch_id, record_id = create_quarantined_batch()
    headers = auth_headers(client)

    batches_response = client.get(
        "/api/ingestion-batches?has_quarantine=true",
        headers=headers,
    )
    assert batches_response.status_code == 200
    batches = batches_response.json()
    assert batches["total"] == 1
    assert batches["items"][0]["id"] == batch_id
    assert batches["items"][0]["source_system_name"] == "FHIR Upload"
    assert batches["items"][0]["quarantine_count"] == 1

    records_response = client.get(
        f"/api/ingestion-batches/{batch_id}/quarantine-records?resource_type=Observation&search=valid%20date",
        headers=headers,
    )
    assert records_response.status_code == 200
    records = records_response.json()
    assert records["total"] == 1
    assert records["items"][0]["id"] == record_id
    assert "raw_payload" not in records["items"][0]


def test_payload_view_is_explicit_and_audited_for_data_reviewer(client):
    batch_id, record_id = create_quarantined_batch()
    headers = auth_headers(client, "reviewer")

    response = client.get(f"/api/quarantine-records/{record_id}/payload", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "id": record_id,
        "ingestion_batch_id": batch_id,
        "raw_payload": {
            "resourceType": "Observation",
            "id": "observation-bad-date",
            "effectiveDateTime": "not-a-date",
        },
    }

    db = SessionLocal()
    try:
        event = db.query(AuditLog).filter(AuditLog.action == "quarantine_payload_viewed").one()
        assert event.username == "reviewer"
        assert event.role == "data_reviewer"
        assert event.resource_type == "quarantine_record"
        assert event.resource_id == str(record_id)
        assert event.event_metadata == {
            "ingestion_batch_id": batch_id,
            "resource_type": "Observation",
            "source_record_id": "observation-bad-date",
            "error_code": "invalid_effective_date",
        }
    finally:
        db.close()


def test_clinician_cannot_access_ingestion_investigation_endpoints(client):
    batch_id, record_id = create_quarantined_batch()
    headers = auth_headers(client, "clinician")

    assert client.get("/api/ingestion-batches", headers=headers).status_code == 403
    assert client.get(
        f"/api/ingestion-batches/{batch_id}/quarantine-records",
        headers=headers,
    ).status_code == 403
    assert client.get(f"/api/quarantine-records/{record_id}/payload", headers=headers).status_code == 403


def test_ingestion_investigation_returns_not_found_for_unknown_records(client):
    headers = auth_headers(client)

    batch_response = client.get(
        "/api/ingestion-batches/999999/quarantine-records",
        headers=headers,
    )
    payload_response = client.get(
        "/api/quarantine-records/999999/payload",
        headers=headers,
    )

    assert batch_response.status_code == 404
    assert batch_response.json()["detail"] == "Ingestion batch not found"
    assert payload_response.status_code == 404
    assert payload_response.json()["detail"] == "Quarantine record not found"
