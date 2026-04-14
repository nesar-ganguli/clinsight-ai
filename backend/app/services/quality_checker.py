from typing import List, Dict, Any


def run_quality_checks(patient) -> List[Dict[str, Any]]:
    alerts = []

    if not patient.full_name:
        alerts.append({
            "severity": "warning",
            "field": "full_name",
            "message": "Patient name is missing"
        })

    if not patient.gender:
        alerts.append({
            "severity": "warning",
            "field": "gender",
            "message": "Patient gender is missing"
        })

    if not patient.birth_date:
        alerts.append({
            "severity": "warning",
            "field": "birth_date",
            "message": "Patient birth date is missing"
        })

    if not patient.conditions or len(patient.conditions) == 0:
        alerts.append({
            "severity": "warning",
            "field": "conditions",
            "message": "No conditions found for this patient"
        })

    if not patient.observations or len(patient.observations) == 0:
        alerts.append({
            "severity": "warning",
            "field": "observations",
            "message": "No observations found for this patient"
        })

    for condition in patient.conditions:
        if not condition.condition_name:
            alerts.append({
                "severity": "warning",
                "field": "condition_name",
                "message": f"Condition name is missing for condition record {condition.id}"
            })

    for observation in patient.observations:
        if observation.value is None or str(observation.value).strip() == "":
            alerts.append({
                "severity": "warning",
                "field": "observation_value",
                "message": f"Observation value is missing for observation record {observation.id}"
            })

    return alerts
