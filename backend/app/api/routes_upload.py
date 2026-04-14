import json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.patient import Patient
from app.models.condition import Condition
from app.models.observation import Observation
from app.services.fhir_parser import parse_fhir_bundle

router = APIRouter()


@router.post("/upload")
async def upload_fhir_bundle(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    try:
        content = await file.read()
        bundle = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Could not decode file as UTF-8")

    if bundle.get("resourceType") != "Bundle":
        raise HTTPException(status_code=400, detail="Uploaded JSON is not a FHIR Bundle")

    parsed_data = parse_fhir_bundle(bundle)
    patient_payload = parsed_data.get("patient")

    if not patient_payload:
        raise HTTPException(status_code=400, detail="No Patient resource found in bundle")

    patient = Patient(
        fhir_patient_id=patient_payload.get("fhir_patient_id"),
        full_name=patient_payload.get("full_name"),
        gender=patient_payload.get("gender"),
        birth_date=patient_payload.get("birth_date")
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    for cond in parsed_data.get("conditions", []):
        db_condition = Condition(
            patient_id=patient.id,
            fhir_condition_id=cond.get("fhir_condition_id"),
            condition_code=cond.get("condition_code"),
            condition_name=cond.get("condition_name"),
            clinical_status=cond.get("clinical_status"),
            onset_date=cond.get("onset_date")
        )
        db.add(db_condition)

    for obs in parsed_data.get("observations", []):
        db_observation = Observation(
            patient_id=patient.id,
            fhir_observation_id=obs.get("fhir_observation_id"),
            observation_code=obs.get("observation_code"),
            observation_name=obs.get("observation_name"),
            value=obs.get("value"),
            unit=obs.get("unit"),
            effective_date=obs.get("effective_date")
        )
        db.add(db_observation)

    db.commit()

    return {
        "message": "FHIR bundle parsed and stored successfully",
        "patient_id": patient.id,
        "resource_counts": parsed_data.get("resource_counts", {})
    }
