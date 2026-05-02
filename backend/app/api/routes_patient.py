from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.schemas.patient import PatientListResponse, PatientOut
from app.services.auth import log_patient_access, require_roles
from app.services.clinical_records import get_patient_record, list_patient_records

router = APIRouter()


@router.get("/patients", response_model=PatientListResponse)
def list_patients(
    search: Optional[str] = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "clinician", "care_coordinator", "data_reviewer")),
):
    return list_patient_records(db, search=search, limit=limit, offset=offset)


@router.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "clinician", "care_coordinator", "data_reviewer")),
):
    patient = get_patient_record(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    log_patient_access(db, user, patient_id)
    return patient
