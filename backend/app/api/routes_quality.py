from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.quality import QualityAlertsResponse
from app.services.clinical_records import get_patient_record
from app.services.quality_checker import run_quality_checks

router = APIRouter()


@router.get("/patients/{patient_id}/quality-alerts", response_model=QualityAlertsResponse)
def get_quality_alerts(patient_id: int, db: Session = Depends(get_db)):
    patient = get_patient_record(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    alerts = run_quality_checks(patient)

    return {
        "patient_id": patient.id,
        "alerts": alerts
    }
