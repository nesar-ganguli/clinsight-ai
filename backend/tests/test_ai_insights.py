from types import SimpleNamespace

from app.services.ai_insights import build_patient_ai_insights


def test_ai_insights_are_grounded_and_evaluated():
    patient = SimpleNamespace(
        id=1,
        fhir_patient_id="patient-001",
        full_name="John Doe",
        gender="male",
        birth_date="1968-04-10",
        conditions=[
            SimpleNamespace(
                id=10,
                fhir_condition_id="condition-1",
                condition_code="44054006",
                condition_name="Diabetes mellitus type 2",
                clinical_status="active",
                onset_date="2024-01-01",
            )
        ],
        observations=[],
        encounters=[],
        medication_requests=[],
        allergies=[],
    )

    report = build_patient_ai_insights(patient)
    citation_ids = {citation["id"] for citation in report["citations"]}

    assert report["patient_id"] == patient.id
    assert report["evaluation"]["unsupported_claims"] == 0
    assert report["evaluation"]["unresolved_citations"] == 0
    assert report["evaluation"]["hallucination_risk"] == "low"
    assert all(
        citation_id in citation_ids
        for section in report["summary_sections"]
        for claim in section["claims"]
        for citation_id in claim["citation_ids"]
    )
    assert any(gap["code"] == "diabetes_a1c_gap" for gap in report["care_gaps"])
    assert any(gap["code"] == "allergy_status_unknown" for gap in report["care_gaps"])
