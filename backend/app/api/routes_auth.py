from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services.audit import write_audit_event
from app.services.auth import authenticate_user, create_access_token, get_current_user


router = APIRouter()


ROLE_PERMISSIONS = {
    "admin": [
        "view_patient_directory",
        "view_patient_charts",
        "view_grounded_ai_summary",
        "view_care_gaps",
        "view_quality_alerts",
        "view_source_metadata",
        "upload_fhir_bundle",
        "import_external_fhir",
    ],
    "clinician": [
        "view_patient_directory",
        "view_patient_charts",
        "view_grounded_ai_summary",
    ],
    "care_coordinator": [
        "view_patient_directory",
        "view_patient_charts",
        "view_care_gaps",
    ],
    "data_reviewer": [
        "view_patient_directory",
        "view_patient_charts",
        "view_quality_alerts",
        "view_source_metadata",
        "upload_fhir_bundle",
        "import_external_fhir",
    ],
}


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    write_audit_event(
        db,
        user=user,
        action="user_login",
        resource_type="user",
        resource_id=str(user.id),
        metadata={"username": user.username, "role": user.role},
    )

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": _user_out(user),
    }


@router.get("/auth/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return _user_out(user)


def _user_out(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "permissions": ROLE_PERMISSIONS.get(user.role, []),
    }
