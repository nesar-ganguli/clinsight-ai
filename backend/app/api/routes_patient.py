from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.patient import Patient
from app.schemas.patient import PatientListResponse, PatientOut

router = APIRouter()


@router.get("/patients", response_model=PatientListResponse)
def list_patients(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Patient)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Patient.full_name.ilike(search_term),
                Patient.fhir_patient_id.ilike(search_term)
            )
        )

    total = query.count()
    patients = (
        query
        .order_by(Patient.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": patients,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = (
        db.query(Patient)
        .options(
            joinedload(Patient.conditions),
            joinedload(Patient.observations),
            joinedload(Patient.encounters),
            joinedload(Patient.medication_requests),
            joinedload(Patient.allergies)
        )
        .filter(Patient.id == patient_id)
        .first()
    )

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient
