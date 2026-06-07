import hashlib
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.external_fhir import ExternalFhirImportResponse, ExternalFhirPatientListResponse
from app.services.audit import write_audit_event
from app.services.auth import require_roles
from app.services.ingestion import ingest_fhir_bundle
from app.services.smart_fhir_client import (
    SMART_HEALTH_IT_FHIR_BASE_URL,
    SmartFhirClientError,
    fetch_smart_patient_bundle,
    search_smart_patients,
)


router = APIRouter()


@router.get("/external-fhir/smart/patients", response_model=ExternalFhirPatientListResponse)
def list_smart_patients(
    search: Optional[str] = Query(default=None, min_length=1, max_length=100),
    count: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    try:
        patients = search_smart_patients(search=search, count=count)
    except SmartFhirClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    write_audit_event(
        db,
        user=user,
        action="external_fhir_patient_searched",
        resource_type="external_fhir_api",
        resource_id="smart-health-it",
        metadata={
            "fhir_base_url": SMART_HEALTH_IT_FHIR_BASE_URL,
            "search": search,
            "count": count,
            "result_count": len(patients),
        },
    )

    return {
        "items": patients,
        "total": len(patients),
        "source_system": "SMART Health IT R4 Sandbox",
        "fhir_base_url": SMART_HEALTH_IT_FHIR_BASE_URL,
    }


@router.post("/external-fhir/smart/import/{patient_id}", response_model=ExternalFhirImportResponse)
def import_smart_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    try:
        bundle = fetch_smart_patient_bundle(patient_id)
        content_hash = hashlib.sha256(json.dumps(bundle, sort_keys=True).encode("utf-8")).hexdigest()
        result = ingest_fhir_bundle(
            bundle,
            db,
            filename=f"smart-health-it-{patient_id}.json",
            content_hash=content_hash,
        )
    except SmartFhirClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message": "SMART Health IT patient imported successfully",
        "source_system": "SMART Health IT R4 Sandbox",
        "external_patient_id": patient_id,
        **result,
    }
