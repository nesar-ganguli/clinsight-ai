from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.allergy_intolerance import AllergyIntolerance
from app.models.condition import Condition
from app.models.encounter import Encounter
from app.models.medication_request import MedicationRequest
from app.models.observation import Observation
from app.models.patient import Patient
from app.services.fhir_parser import parse_fhir_bundle


def ingest_fhir_bundle(bundle: Dict[str, Any], db: Session) -> Dict[str, Any]:
    parsed_data = parse_fhir_bundle(bundle)
    patient_payload = parsed_data.get("patient")

    if not patient_payload:
        raise ValueError("No Patient resource found in bundle")

    patient = None
    import_mode = "created"
    fhir_patient_id = patient_payload.get("fhir_patient_id")

    if fhir_patient_id:
        patient = (
            db.query(Patient)
            .filter(Patient.fhir_patient_id == fhir_patient_id)
            .first()
        )

    if patient:
        import_mode = "updated"
        patient.full_name = patient_payload.get("full_name")
        patient.gender = patient_payload.get("gender")
        patient.birth_date = patient_payload.get("birth_date")

        db.query(AllergyIntolerance).filter(AllergyIntolerance.patient_id == patient.id).delete()
        db.query(Condition).filter(Condition.patient_id == patient.id).delete()
        db.query(Encounter).filter(Encounter.patient_id == patient.id).delete()
        db.query(MedicationRequest).filter(MedicationRequest.patient_id == patient.id).delete()
        db.query(Observation).filter(Observation.patient_id == patient.id).delete()
    else:
        patient = Patient(
            fhir_patient_id=fhir_patient_id,
            full_name=patient_payload.get("full_name"),
            gender=patient_payload.get("gender"),
            birth_date=patient_payload.get("birth_date")
        )
        db.add(patient)
        db.flush()

    for cond in parsed_data.get("conditions", []):
        db.add(
            Condition(
                patient_id=patient.id,
                fhir_condition_id=cond.get("fhir_condition_id"),
                condition_code=cond.get("condition_code"),
                condition_name=cond.get("condition_name"),
                clinical_status=cond.get("clinical_status"),
                onset_date=cond.get("onset_date")
            )
        )

    for obs in parsed_data.get("observations", []):
        db.add(
            Observation(
                patient_id=patient.id,
                fhir_observation_id=obs.get("fhir_observation_id"),
                observation_code=obs.get("observation_code"),
                observation_name=obs.get("observation_name"),
                value=obs.get("value"),
                unit=obs.get("unit"),
                effective_date=obs.get("effective_date")
            )
        )

    for encounter in parsed_data.get("encounters", []):
        db.add(
            Encounter(
                patient_id=patient.id,
                fhir_encounter_id=encounter.get("fhir_encounter_id"),
                status=encounter.get("status"),
                encounter_class=encounter.get("encounter_class"),
                encounter_type=encounter.get("encounter_type"),
                period_start=encounter.get("period_start"),
                period_end=encounter.get("period_end")
            )
        )

    for medication in parsed_data.get("medication_requests", []):
        db.add(
            MedicationRequest(
                patient_id=patient.id,
                fhir_medication_request_id=medication.get("fhir_medication_request_id"),
                status=medication.get("status"),
                intent=medication.get("intent"),
                medication_code=medication.get("medication_code"),
                medication_name=medication.get("medication_name"),
                authored_on=medication.get("authored_on")
            )
        )

    for allergy in parsed_data.get("allergies", []):
        db.add(
            AllergyIntolerance(
                patient_id=patient.id,
                fhir_allergy_id=allergy.get("fhir_allergy_id"),
                clinical_status=allergy.get("clinical_status"),
                verification_status=allergy.get("verification_status"),
                allergy_code=allergy.get("allergy_code"),
                allergy_name=allergy.get("allergy_name"),
                criticality=allergy.get("criticality"),
                recorded_date=allergy.get("recorded_date")
            )
        )

    db.commit()
    db.refresh(patient)

    return {
        "patient_id": patient.id,
        "import_mode": import_mode,
        "resource_counts": parsed_data.get("resource_counts", {}),
    }
