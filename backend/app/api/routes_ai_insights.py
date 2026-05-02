from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.patient import Patient
from app.schemas.ai_insights import PatientAiInsightsResponse
from app.services.ai_insights import build_patient_ai_insights

router = APIRouter()


@router.get("/patients/{patient_id}/ai-insights", response_model=PatientAiInsightsResponse)
def get_patient_ai_insights(patient_id: int, db: Session = Depends(get_db)):
    patient = (
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

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return build_patient_ai_insights(patient)
