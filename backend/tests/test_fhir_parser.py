import json
from pathlib import Path

from app.services.fhir_parser import parse_fhir_bundle


SAMPLE_BUNDLE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "patient_bundle_1.json"


def test_parse_fhir_bundle_extracts_supported_resources():
    bundle = json.loads(SAMPLE_BUNDLE_PATH.read_text(encoding="utf-8"))

    parsed = parse_fhir_bundle(bundle)

    assert parsed["patient"]["fhir_patient_id"] == "patient-001"
    assert parsed["patient"]["full_name"] == "John Doe"
    assert len(parsed["conditions"]) == 2
    assert len(parsed["observations"]) == 2
    assert len(parsed["encounters"]) == 1
    assert len(parsed["medication_requests"]) == 1
    assert len(parsed["allergies"]) == 1
    assert parsed["resource_counts"]["Patient"] == 1
    assert parsed["resource_counts"]["Condition"] == 2
    assert parsed["resource_counts"]["Observation"] == 2
    assert parsed["resource_counts"]["Encounter"] == 1
    assert parsed["resource_counts"]["MedicationRequest"] == 1
    assert parsed["resource_counts"]["AllergyIntolerance"] == 1


def test_parse_fhir_bundle_handles_codeable_concept_lists():
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "smart-patient-001",
                    "name": [{"given": ["Smart"], "family": "Patient"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "smart-encounter-001",
                    "subject": {"reference": "Patient/smart-patient-001"},
                    "status": "finished",
                    "class": {"code": "AMB"},
                    "type": [
                        {
                            "coding": [
                                {
                                    "code": "185349003",
                                    "display": "Encounter for check up",
                                }
                            ]
                        }
                    ],
                }
            },
        ],
    }

    parsed = parse_fhir_bundle(bundle)

    assert parsed["encounters"][0]["encounter_type"] == "Encounter for check up"
