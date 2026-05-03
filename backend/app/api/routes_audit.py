from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, DbtAuditRequest
from app.services.audit import write_audit_event
from app.services.auth import require_roles


router = APIRouter()


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    patient_id: Optional[int] = Query(default=None),
    action: Optional[str] = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    query = db.query(AuditLog)
    if patient_id is not None:
        query = query.filter(AuditLog.patient_id == patient_id)
    if action:
        query = query.filter(AuditLog.action == action)

    total = query.count()
    items = (
        query.order_by(AuditLog.event_timestamp.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/audit-logs/dbt-transformation")
def record_dbt_transformation_audit(
    payload: DbtAuditRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    action = "dbt_transformation_completed" if payload.status == "completed" else "dbt_transformation_triggered"
    audit_log = write_audit_event(
        db,
        user=user,
        action=action,
        resource_type="dbt_transformation",
        resource_id=payload.invocation_id,
        metadata={
            "status": payload.status,
            "selected_models": payload.selected_models,
            **payload.metadata,
        },
    )
    return {"id": audit_log.id, "action": audit_log.action}
