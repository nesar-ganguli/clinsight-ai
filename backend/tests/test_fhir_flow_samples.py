import json
from pathlib import Path

import pytest

from app.services.fhir_parser import parse_fhir_bundle
from app.services.ingestion import _is_smart_health_it_bundle


FLOW_FIXTURE_DIR = Path(__file__).resolve().parent.parent / "sample_data" / "fhir_flow_tests"


@pytest.mark.parametrize(
    ("filename", "accepted", "rejected", "unsupported"),
    [
        ("01_valid_create_then_exact_reupload.json", 3, 0, 0),
        ("02_partial_success_quarantine_and_unsupported.json", 3, 3, 1),
        ("04_additional_patient_quarantined.json", 2, 1, 0),
        ("05_malformed_entries_quarantined.json", 2, 2, 0),
        ("06_unsupported_resources_counted_not_quarantined.json", 2, 0, 2),
        ("07a_default_source_same_patient_id.json", 2, 0, 0),
        ("07b_smart_source_same_patient_id_creates_separate_patient.json", 2, 0, 0),
        ("08a_same_source_initial_with_two_conditions.json", 3, 0, 0),
        ("08b_same_source_update_omits_existing_condition.json", 2, 0, 0),
    ],
)
def test_nonfatal_flow_fixtures_match_their_documented_classification(
    filename,
    accepted,
    rejected,
    unsupported,
):
    bundle = json.loads((FLOW_FIXTURE_DIR / filename).read_text(encoding="utf-8"))

    parsed = parse_fhir_bundle(bundle)
    accepted_count = 1 + sum(
        len(parsed[collection])
        for collection in (
            "conditions",
            "observations",
            "encounters",
            "medication_requests",
            "allergies",
        )
    )

    assert accepted_count == accepted
    assert len(parsed["quarantined_resources"]) == rejected
    assert parsed["unsupported_count"] == unsupported
    assert parsed["record_count"] == accepted + rejected + unsupported


@pytest.mark.parametrize(
    "filename",
    [
        "03_batch_fatal_no_patient.json",
        "09_batch_fatal_patient_missing_id.json",
    ],
)
def test_batch_fatal_flow_fixtures_have_no_usable_patient(filename):
    bundle = json.loads((FLOW_FIXTURE_DIR / filename).read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="No usable Patient resource found in bundle"):
        parse_fhir_bundle(bundle)


def test_source_identity_pair_uses_distinct_source_markers():
    default_bundle = json.loads(
        (FLOW_FIXTURE_DIR / "07a_default_source_same_patient_id.json").read_text(encoding="utf-8")
    )
    smart_bundle = json.loads(
        (
            FLOW_FIXTURE_DIR
            / "07b_smart_source_same_patient_id_creates_separate_patient.json"
        ).read_text(encoding="utf-8")
    )

    assert _is_smart_health_it_bundle(default_bundle) is False
    assert _is_smart_health_it_bundle(smart_bundle) is True
    assert (
        default_bundle["entry"][0]["resource"]["id"]
        == smart_bundle["entry"][0]["resource"]["id"]
        == "flow-shared-patient-id"
    )
