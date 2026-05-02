from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ai_insights import PatientAiInsightsResponse
from app.services.ai_insights import build_patient_ai_insights
from app.services.clinical_records import get_patient_record

router = APIRouter()


@router.get("/patients/{patient_id}/ai-insights", response_model=PatientAiInsightsResponse)
def get_patient_ai_insights(patient_id: int, db: Session = Depends(get_db)):
    patient = get_patient_record(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return build_patient_ai_insights(patient)
