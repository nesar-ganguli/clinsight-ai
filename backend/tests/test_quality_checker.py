from types import SimpleNamespace

from app.services.quality_checker import run_quality_checks


def test_quality_checker_returns_structured_alerts_for_missing_data():
    patient = SimpleNamespace(
        full_name=None,
        gender=None,
        birth_date=None,
        conditions=[SimpleNamespace(id=10, condition_name=None)],
        observations=[SimpleNamespace(id=20, value=None, unit=None, observation_code="8867-4")],
        encounters=[SimpleNamespace(id=30, status=None, period_start=None)],
        medication_requests=[SimpleNamespace(id=40, medication_name=None, status=None)],
        allergies=[SimpleNamespace(id=50, allergy_name=None, verification_status=None)]
    )

    alerts = run_quality_checks(patient)
    alert_codes = {alert["code"] for alert in alerts}

    assert "missing_patient_name" in alert_codes
    assert "missing_patient_gender" in alert_codes
    assert "missing_patient_birth_date" in alert_codes
    assert "missing_condition_name" in alert_codes
    assert "missing_observation_value" in alert_codes
    assert "missing_encounter_status" in alert_codes
    assert "missing_encounter_start" in alert_codes
    assert "missing_medication_name" in alert_codes
    assert "missing_medication_status" in alert_codes
    assert "missing_allergy_name" in alert_codes
    assert "missing_allergy_verification_status" in alert_codes


def test_quality_checker_sorts_warning_before_info():
    patient = SimpleNamespace(
        full_name="John Doe",
        gender="male",
        birth_date="1968-04-10",
        conditions=[],
        observations=[],
        encounters=[],
        medication_requests=[],
        allergies=[]
    )

    alerts = run_quality_checks(patient)

    assert alerts[0]["severity"] == "warning"
    assert alerts[-1]["severity"] == "info"
