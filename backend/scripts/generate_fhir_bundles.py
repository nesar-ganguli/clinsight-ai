import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.services.clinical_records import get_patient_record, list_patient_records


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "generated_fhir_bundles"
GENERATED_FHIR_SOURCE_MARKER = "clinsight-generated-fhir-bundle"


def build_fhir_bundle(patient) -> Dict[str, Any]:
    patient_fhir_id = _resource_id("patient", patient.id)
    entries = [_entry(_patient_resource(patient, patient_fhir_id))]

    for encounter in getattr(patient, "encounters", []):
        entries.append(_entry(_encounter_resource(encounter, patient_fhir_id)))

    for condition in getattr(patient, "conditions", []):
        entries.append(_entry(_condition_resource(condition, patient_fhir_id)))

    for observation in getattr(patient, "observations", []):
        entries.append(_entry(_observation_resource(observation, patient_fhir_id)))

    for medication in getattr(patient, "medication_requests", []):
        entries.append(_entry(_medication_request_resource(medication, patient_fhir_id)))

    for allergy in getattr(patient, "allergies", []):
        entries.append(_entry(_allergy_resource(allergy, patient_fhir_id)))

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {
            "source": GENERATED_FHIR_SOURCE_MARKER,
            "tag": [
                {
                    "system": "https://clinsight.ai/source-type",
                    "code": "generated-fhir-bundle",
                    "display": "Generated FHIR bundle",
                }
            ],
        },
        "entry": entries,
    }


def write_fhir_bundles(
    patients: Iterable[Any],
    output_dir: Path,
) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written_paths = []
    for patient in patients:
        bundle = build_fhir_bundle(patient)
        filename = f"patient_{_safe_filename(patient.id)}_bundle.json"
        path = output_dir / filename
        path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
        written_paths.append(path)
    return written_paths


def _patient_resource(patient, patient_fhir_id: str) -> Dict[str, Any]:
    given, family = _split_name(getattr(patient, "full_name", None))
    resource = {
        "resourceType": "Patient",
        "id": patient_fhir_id,
        "name": [
            {
                "use": "official",
                "given": given,
                "family": family,
            }
        ],
    }

    if getattr(patient, "gender", None):
        resource["gender"] = patient.gender
    if getattr(patient, "birth_date", None):
        resource["birthDate"] = _date_only(patient.birth_date)

    return resource


def _encounter_resource(encounter, patient_fhir_id: str) -> Dict[str, Any]:
    resource = {
        "resourceType": "Encounter",
        "id": _resource_id("encounter", encounter.id),
        "status": getattr(encounter, "status", None) or "unknown",
        "subject": _patient_reference(patient_fhir_id),
    }
    if getattr(encounter, "encounter_class", None):
        resource["class"] = {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": encounter.encounter_class,
            "display": encounter.encounter_class,
        }
    if getattr(encounter, "encounter_type", None):
        resource["type"] = _codeable_concept(None, encounter.encounter_type)

    period = {}
    if getattr(encounter, "period_start", None):
        period["start"] = encounter.period_start
    if getattr(encounter, "period_end", None):
        period["end"] = encounter.period_end
    if period:
        resource["period"] = period

    return resource


def _condition_resource(condition, patient_fhir_id: str) -> Dict[str, Any]:
    resource = {
        "resourceType": "Condition",
        "id": _resource_id("condition", condition.id),
        "subject": _patient_reference(patient_fhir_id),
        "code": _codeable_concept(
            getattr(condition, "condition_code", None),
            getattr(condition, "condition_name", None),
        ),
    }
    if getattr(condition, "clinical_status", None):
        resource["clinicalStatus"] = _codeable_concept(condition.clinical_status, condition.clinical_status)
    if getattr(condition, "onset_date", None):
        resource["onsetDateTime"] = condition.onset_date
    return resource


def _observation_resource(observation, patient_fhir_id: str) -> Dict[str, Any]:
    resource = {
        "resourceType": "Observation",
        "id": _resource_id("observation", observation.id),
        "status": "final",
        "subject": _patient_reference(patient_fhir_id),
        "code": _codeable_concept(
            getattr(observation, "observation_code", None),
            getattr(observation, "observation_name", None),
        ),
    }
    if getattr(observation, "effective_date", None):
        resource["effectiveDateTime"] = observation.effective_date

    value = getattr(observation, "value", None)
    if value is not None and str(value).strip() != "":
        numeric_value = _to_number(value)
        if numeric_value is not None:
            resource["valueQuantity"] = {
                "value": numeric_value,
                "unit": getattr(observation, "unit", None),
            }
        else:
            resource["valueString"] = str(value)

    return resource


def _medication_request_resource(medication, patient_fhir_id: str) -> Dict[str, Any]:
    resource = {
        "resourceType": "MedicationRequest",
        "id": _resource_id("medication-request", medication.id),
        "status": getattr(medication, "status", None) or "unknown",
        "intent": getattr(medication, "intent", None) or "order",
        "subject": _patient_reference(patient_fhir_id),
        "medicationCodeableConcept": _codeable_concept(
            getattr(medication, "medication_code", None),
            getattr(medication, "medication_name", None),
        ),
    }
    if getattr(medication, "authored_on", None):
        resource["authoredOn"] = medication.authored_on
    return resource


def _allergy_resource(allergy, patient_fhir_id: str) -> Dict[str, Any]:
    resource = {
        "resourceType": "AllergyIntolerance",
        "id": _resource_id("allergy", allergy.id),
        "patient": _patient_reference(patient_fhir_id),
        "code": _codeable_concept(
            getattr(allergy, "allergy_code", None),
            getattr(allergy, "allergy_name", None),
        ),
    }
    if getattr(allergy, "clinical_status", None):
        resource["clinicalStatus"] = _codeable_concept(allergy.clinical_status, allergy.clinical_status)
    if getattr(allergy, "verification_status", None):
        resource["verificationStatus"] = _codeable_concept(allergy.verification_status, allergy.verification_status)
    if getattr(allergy, "criticality", None):
        resource["criticality"] = allergy.criticality
    if getattr(allergy, "recorded_date", None):
        resource["recordedDate"] = allergy.recorded_date
    return resource


def _entry(resource: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "fullUrl": f"urn:uuid:{resource['resourceType']}-{resource['id']}",
        "resource": resource,
    }


def _patient_reference(patient_fhir_id: str) -> Dict[str, str]:
    return {"reference": f"Patient/{patient_fhir_id}"}


def _codeable_concept(code: Optional[str], display: Optional[str]) -> Dict[str, Any]:
    concept: Dict[str, Any] = {}
    if code:
        concept["coding"] = [{"code": str(code), "display": display or str(code)}]
    if display:
        concept["text"] = display
    return concept


def _resource_id(prefix: str, record_id: Any) -> str:
    return f"{prefix}-{record_id}"


def _split_name(full_name: Optional[str]) -> tuple:
    if not full_name:
        return [], None
    parts = str(full_name).split()
    if len(parts) == 1:
        return [parts[0]], None
    return parts[:-1], parts[-1]


def _date_only(value: Any) -> str:
    return str(value).split("T", 1)[0]


def _to_number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_filename(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate FHIR Bundle JSON files from curated clinical records.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of patient bundles to generate.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where generated FHIR Bundle JSON files should be written.",
    )
    parser.add_argument(
        "--ingestion-batch-id",
        default=None,
        help="Optional dbt curated ingestion batch id to export.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be greater than 0")

    db = SessionLocal()
    try:
        summaries = list_patient_records(
            db,
            ingestion_batch_id=args.ingestion_batch_id,
            limit=args.limit,
            offset=0,
        )["items"]
        patients = [get_patient_record(db, summary.id) for summary in summaries]
        patients = [patient for patient in patients if patient is not None]
        paths = write_fhir_bundles(patients, args.output)
    finally:
        db.close()

    print(f"Generated {len(paths)} FHIR bundle(s)")
    print(f"output={args.output}")
    for path in paths:
        print(f"- {path}")


if __name__ == "__main__":
    main()
