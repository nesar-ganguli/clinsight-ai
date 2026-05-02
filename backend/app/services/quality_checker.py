from typing import Any, Callable, Dict, List


QualityRule = Callable[[Any], List[Dict[str, Any]]]


def build_alert(code: str, severity: str, category: str, field: str, message: str) -> Dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "category": category,
        "field": field,
        "message": message
    }


def check_demographics(patient) -> List[Dict[str, Any]]:
    alerts = []

    if not patient.full_name:
        alerts.append(build_alert("missing_patient_name", "warning", "demographics", "full_name", "Patient name is missing"))

    if not patient.gender:
        alerts.append(build_alert("missing_patient_gender", "warning", "demographics", "gender", "Patient gender is missing"))

    if not patient.birth_date:
        alerts.append(build_alert("missing_patient_birth_date", "warning", "demographics", "birth_date", "Patient birth date is missing"))

    return alerts


def check_clinical_coverage(patient) -> List[Dict[str, Any]]:
    alerts = []

    resource_expectations = [
        ("conditions", patient.conditions, "warning", "No conditions found for this patient"),
        ("observations", patient.observations, "warning", "No observations found for this patient"),
        ("encounters", patient.encounters, "warning", "No encounters found for this patient"),
        ("medication_requests", patient.medication_requests, "info", "No medication requests found for this patient"),
        ("allergies", patient.allergies, "info", "No allergies found for this patient")
    ]

    for field, records, severity, message in resource_expectations:
        if not records:
            alerts.append(build_alert(f"missing_{field}", severity, "coverage", field, message))

    return alerts


def check_condition_quality(patient) -> List[Dict[str, Any]]:
    alerts = []

    for condition in patient.conditions:
        if not condition.condition_name:
            alerts.append(
                build_alert(
                    "missing_condition_name",
                    "warning",
                    "conditions",
                    "condition_name",
                    f"Condition name is missing for condition record {condition.id}"
                )
            )

    return alerts


def check_observation_quality(patient) -> List[Dict[str, Any]]:
    alerts = []

    for observation in patient.observations:
        if observation.value is None or str(observation.value).strip() == "":
            alerts.append(
                build_alert(
                    "missing_observation_value",
                    "warning",
                    "observations",
                    "observation_value",
                    f"Observation value is missing for observation record {observation.id}"
                )
            )

        if observation.value and not observation.unit and observation.observation_code != "85354-9":
            alerts.append(
                build_alert(
                    "missing_observation_unit",
                    "info",
                    "observations",
                    "unit",
                    f"Observation unit is missing for observation record {observation.id}"
                )
            )

    return alerts


def check_encounter_quality(patient) -> List[Dict[str, Any]]:
    alerts = []

    for encounter in patient.encounters:
        if not encounter.status:
            alerts.append(
                build_alert(
                    "missing_encounter_status",
                    "warning",
                    "encounters",
                    "status",
                    f"Encounter status is missing for encounter record {encounter.id}"
                )
            )

        if not encounter.period_start:
            alerts.append(
                build_alert(
                    "missing_encounter_start",
                    "warning",
                    "encounters",
                    "period_start",
                    f"Encounter start time is missing for encounter record {encounter.id}"
                )
            )

    return alerts


def check_medication_quality(patient) -> List[Dict[str, Any]]:
    alerts = []

    for medication in patient.medication_requests:
        if not medication.medication_name:
            alerts.append(
                build_alert(
                    "missing_medication_name",
                    "warning",
                    "medications",
                    "medication_name",
                    f"Medication name is missing for medication request record {medication.id}"
                )
            )

        if not medication.status:
            alerts.append(
                build_alert(
                    "missing_medication_status",
                    "warning",
                    "medications",
                    "status",
                    f"Medication status is missing for medication request record {medication.id}"
                )
            )

    return alerts


def check_allergy_quality(patient) -> List[Dict[str, Any]]:
    alerts = []

    for allergy in patient.allergies:
        if not allergy.allergy_name:
            alerts.append(
                build_alert(
                    "missing_allergy_name",
                    "warning",
                    "allergies",
                    "allergy_name",
                    f"Allergy name is missing for allergy record {allergy.id}"
                )
            )

        if not allergy.verification_status:
            alerts.append(
                build_alert(
                    "missing_allergy_verification_status",
                    "info",
                    "allergies",
                    "verification_status",
                    f"Allergy verification status is missing for allergy record {allergy.id}"
                )
            )

    return alerts


QUALITY_RULES: List[QualityRule] = [
    check_demographics,
    check_clinical_coverage,
    check_condition_quality,
    check_observation_quality,
    check_encounter_quality,
    check_medication_quality,
    check_allergy_quality,
]


def run_quality_checks(patient) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []

    for rule in QUALITY_RULES:
        alerts.extend(rule(patient))

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda alert: (severity_order.get(alert["severity"], 99), alert["code"], alert["message"]))
    return alerts
