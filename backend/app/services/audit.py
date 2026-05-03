from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def write_audit_event(
    db: Session,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    user: Optional[User] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    role: Optional[str] = None,
    commit: bool = True,
) -> AuditLog:
    audit_log = AuditLog(
        user_id=user.id if user else user_id,
        username=user.username if user else username,
        role=user.role if user else role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        patient_id=_patient_id(resource_type, resource_id, metadata),
        event_timestamp=datetime.now(timezone.utc),
        event_metadata=metadata or {},
    )
    db.add(audit_log)
    if commit:
        try:
            db.commit()
            db.refresh(audit_log)
        except OperationalError as exc:
            db.rollback()
            if _is_sqlite_lock_error(exc):
                return audit_log
            raise
    return audit_log


def _is_sqlite_lock_error(exc: OperationalError) -> bool:
    return "database is locked" in str(exc).lower()


def _patient_id(
    resource_type: Optional[str],
    resource_id: Optional[str],
    metadata: Optional[Dict[str, Any]],
) -> Optional[int]:
    if resource_type == "patient" and resource_id is not None:
        try:
            return int(resource_id)
        except (TypeError, ValueError):
            return None

    if metadata and metadata.get("patient_id") is not None:
        try:
            return int(metadata["patient_id"])
        except (TypeError, ValueError):
            return None

    return None
