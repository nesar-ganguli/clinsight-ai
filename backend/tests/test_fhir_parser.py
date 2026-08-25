import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.temporal import parse_fhir_datetime
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
    assert parsed["conditions"][0]["onset_date"] == datetime(2024, 5, 1, tzinfo=timezone.utc)
    assert parsed["observations"][0]["effective_date"] == datetime(
        2026, 3, 15, 10, 30, tzinfo=timezone.utc
    )


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


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("2026-04-01", datetime(2026, 4, 1, tzinfo=timezone.utc)),
        ("2026-04-01T14:30:00Z", datetime(2026, 4, 1, 14, 30, tzinfo=timezone.utc)),
        ("2026-04-01T10:30:00-04:00", datetime(2026, 4, 1, 14, 30, tzinfo=timezone.utc)),
        (None, None),
        ("", None),
        ("not-a-clinical-date", None),
        ("2026-99-01", None),
    ],
)
def test_parse_fhir_datetime_normalizes_supported_values(raw_value, expected):
    assert parse_fhir_datetime(raw_value) == expected
