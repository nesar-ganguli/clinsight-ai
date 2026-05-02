import json
import statistics
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import joinedload

from app.core.database import SessionLocal
from app.models.allergy_intolerance import AllergyIntolerance
from app.models.condition import Condition
from app.models.encounter import Encounter
from app.models.medication_request import MedicationRequest
from app.models.observation import Observation
from app.models.patient import Patient
from app.services.ai_insights import build_patient_ai_insights
from app.services.ingestion import ingest_fhir_bundle
from app.services.quality_checker import run_quality_checks


SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "sample_data"
EXPECTED_QUALITY_ALERTS = {
    "patient-001": set(),
    "patient-002": {
        "missing_patient_gender",
        "missing_observations",
        "missing_encounters",
        "missing_medication_requests",
        "missing_allergies",
    },
    "patient-003": set(),
}


def reset_database(db):
    db.query(AllergyIntolerance).delete()
    db.query(Condition).delete()
    db.query(Encounter).delete()
    db.query(MedicationRequest).delete()
    db.query(Observation).delete()
    db.query(Patient).delete()
    db.commit()


def load_bundle(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def get_patient(db, patient_id: int):
    return (
        db.query(Patient)
        .options(
            joinedload(Patient.conditions),
            joinedload(Patient.observations),
            joinedload(Patient.encounters),
            joinedload(Patient.medication_requests),
            joinedload(Patient.allergies),
        )
        .filter(Patient.id == patient_id)
        .first()
    )


def main():
    db = SessionLocal()
    try:
        reset_database(db)

        ingestion_results = []
        patients = []
        for bundle_path in sorted(SAMPLE_DATA_DIR.glob("patient_bundle_*.json")):
            bundle = load_bundle(bundle_path)
            started = time.perf_counter()
            result = ingest_fhir_bundle(bundle, db)
            elapsed_ms = (time.perf_counter() - started) * 1000
            patient = get_patient(db, result["patient_id"])
            patients.append(patient)
            ingestion_results.append(
                {
                    "bundle": bundle_path.name,
                    "patient": patient.fhir_patient_id,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "resource_count": sum(result["resource_counts"].values()),
                }
            )

        predicted_alerts = []
        expected_alerts = []
        true_positive_alerts = 0
        for patient in patients:
            patient_expected = EXPECTED_QUALITY_ALERTS.get(patient.fhir_patient_id, set())
            patient_predicted = {alert["code"] for alert in run_quality_checks(patient)}
            predicted_alerts.extend(patient_predicted)
            expected_alerts.extend(patient_expected)
            true_positive_alerts += len(patient_predicted.intersection(patient_expected))

        alert_precision = true_positive_alerts / len(predicted_alerts) if predicted_alerts else 1.0
        alert_recall = true_positive_alerts / len(expected_alerts) if expected_alerts else 1.0

        insight_reports = [build_patient_ai_insights(patient) for patient in patients]
        grounded_claims = [report["evaluation"]["grounded_claims"] for report in insight_reports]
        unsupported_claims = sum(report["evaluation"]["unsupported_claims"] for report in insight_reports)
        unresolved_citations = sum(report["evaluation"]["unresolved_citations"] for report in insight_reports)
        hallucination_risks = {}
        for report in insight_reports:
            risk = report["evaluation"]["hallucination_risk"]
            hallucination_risks[risk] = hallucination_risks.get(risk, 0) + 1

        metrics = {
            "ingestion_speed": {
                "bundles": ingestion_results,
                "average_ms": round(statistics.mean(result["elapsed_ms"] for result in ingestion_results), 2),
                "fastest_ms": round(min(result["elapsed_ms"] for result in ingestion_results), 2),
                "slowest_ms": round(max(result["elapsed_ms"] for result in ingestion_results), 2),
            },
            "alert_precision": {
                "expected_alert_count": len(expected_alerts),
                "predicted_alert_count": len(predicted_alerts),
                "true_positive_count": true_positive_alerts,
                "precision": round(alert_precision, 2),
                "recall": round(alert_recall, 2),
            },
            "summary_evaluation": {
                "patients_evaluated": len(patients),
                "average_grounded_claims": round(statistics.mean(grounded_claims), 2),
                "unsupported_claims": unsupported_claims,
                "unresolved_citations": unresolved_citations,
                "hallucination_risk_distribution": hallucination_risks,
            },
        }

        print(json.dumps(metrics, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
