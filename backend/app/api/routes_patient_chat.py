from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.patient_chat import PatientChatRequest, PatientChatResponse
from app.services.audit import write_audit_event
from app.services.auth import require_roles
from app.services.clinical_records import get_patient_record
from app.services.patient_chat import answer_patient_question


router = APIRouter()


@router.post("/patients/{patient_id}/chat", response_model=PatientChatResponse)
def chat_with_patient_record(
    patient_id: int,
    payload: PatientChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "clinician", "care_coordinator", "data_reviewer")),
):
    patient = get_patient_record(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = answer_patient_question(patient, payload.question)
    write_audit_event(
        db,
        user=user,
        action="patient_chat_question_asked",
        resource_type="patient",
        resource_id=str(patient_id),
        metadata={
            "patient_id": patient_id,
            "question": payload.question,
            "citation_count": len(result["citations"]),
            "llm_used": result["llm_used"],
            "refused": result["refused"],
        },
    )
    return result
