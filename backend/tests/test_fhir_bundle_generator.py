import json
from types import SimpleNamespace

from app.core.database import SessionLocal
from app.models.source_system import SourceSystem
from app.services.fhir_parser import parse_fhir_bundle
from scripts.generate_fhir_bundles import build_fhir_bundle, write_fhir_bundles


def test_build_fhir_bundle_preserves_resource_references():
    patient = synthetic_patient()

    bundle = build_fhir_bundle(patient)
    resources = [entry["resource"] for entry in bundle["entry"]]
    resource_types = [resource["resourceType"] for resource in resources]

    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["meta"]["source"] == "clinsight-generated-fhir-bundle"
    assert resource_types == [
        "Patient",
        "Encounter",
        "Condition",
        "Observation",
        "MedicationRequest",
        "AllergyIntolerance",
    ]

    patient_resource = resources[0]
    assert patient_resource["id"] == "patient-123"
    assert patient_resource["name"][0]["given"] == ["Avery"]
    assert patient_resource["name"][0]["family"] == "Morgan"

    patient_reference = "Patient/patient-123"
    assert resources[1]["subject"]["reference"] == patient_reference
    assert resources[2]["subject"]["reference"] == patient_reference
    assert resources[3]["subject"]["reference"] == patient_reference
    assert resources[4]["subject"]["reference"] == patient_reference
    assert resources[5]["patient"]["reference"] == patient_reference


def test_generated_bundle_is_supported_by_existing_fhir_parser():
    parsed = parse_fhir_bundle(build_fhir_bundle(synthetic_patient()))

    assert parsed["patient"]["fhir_patient_id"] == "patient-123"
    assert parsed["patient"]["full_name"] == "Avery Morgan"
    assert len(parsed["encounters"]) == 1
    assert len(parsed["conditions"]) == 1
    assert len(parsed["observations"]) == 1
    assert len(parsed["medication_requests"]) == 1
    assert len(parsed["allergies"]) == 1
    assert parsed["observations"][0]["value"] == "8.2"


def test_write_fhir_bundles_creates_uploadable_json(client, tmp_path):
    paths = write_fhir_bundles([synthetic_patient()], tmp_path)

    assert len(paths) == 1
    bundle = json.loads(paths[0].read_text(encoding="utf-8"))

    response = client.post(
        "/api/upload",
        files={"file": (paths[0].name, json.dumps(bundle), "application/json")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["import_mode"] == "created"
    assert payload["resource_counts"] == {
        "Patient": 1,
        "Encounter": 1,
        "Condition": 1,
        "Observation": 1,
        "MedicationRequest": 1,
        "AllergyIntolerance": 1,
    }

    db = SessionLocal()
    try:
        source_system = db.query(SourceSystem).filter(SourceSystem.name == "ClinSight Generated FHIR Bundle").one()
        assert source_system.system_type == "generated_fhir_bundle"
    finally:
        db.close()


def synthetic_patient():
    return SimpleNamespace(
        id=123,
        fhir_patient_id=None,
        full_name="Avery Morgan",
        gender="female",
        birth_date="1978-04-12",
        encounters=[
            SimpleNamespace(
                id=201,
                fhir_encounter_id=None,
                status="finished",
                encounter_class="hospital",
                encounter_type="office_visit",
                period_start="2026-04-01T08:00:00",
                period_end="2026-04-01T16:00:00",
            )
        ],
        conditions=[
            SimpleNamespace(
                id=301,
                fhir_condition_id=None,
                condition_code="E11.9",
                condition_name="Type 2 Diabetes Mellitus Without Complications",
                clinical_status="active",
                onset_date="2026-01-01",
            )
        ],
        observations=[
            SimpleNamespace(
                id=401,
                fhir_observation_id=None,
                observation_code="4548-4",
                observation_name="Hemoglobin A1c",
                value="8.2",
                unit="%",
                effective_date="2026-04-01T14:00:00",
            )
        ],
        medication_requests=[
            SimpleNamespace(
                id=501,
                fhir_medication_request_id=None,
                status="active",
                intent="order",
                medication_code="RXN-860975",
                medication_name="Metformin 500 Mg Oral Tablet",
                authored_on="2026-04-01T11:00:00",
            )
        ],
        allergies=[
            SimpleNamespace(
                id=601,
                fhir_allergy_id=None,
                clinical_status="active",
                verification_status="confirmed",
                allergy_code="7980",
                allergy_name="Penicillin",
                criticality="high",
                recorded_date="2026-04-01T10:00:00",
            )
        ],
    )
