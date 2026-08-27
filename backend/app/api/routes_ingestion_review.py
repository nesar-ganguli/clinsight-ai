from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ingestion_batch import IngestionBatch
from app.models.quarantine_record import QuarantineRecord
from app.models.user import User
from app.schemas.ingestion_review import (
    IngestionBatchListResponse,
    QuarantinePayloadOut,
    QuarantineRecordListResponse,
)
from app.services.audit import write_audit_event
from app.services.auth import require_roles
from app.services.ingestion_review import list_ingestion_batches, list_quarantine_records


router = APIRouter()


@router.get("/ingestion-batches", response_model=IngestionBatchListResponse)
def get_ingestion_batches(
    batch_status: Optional[str] = Query(default=None, alias="status", max_length=100),
    source_system: Optional[str] = Query(default=None, max_length=255),
    has_quarantine: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    return list_ingestion_batches(
        db,
        status=batch_status,
        source_system=source_system,
        has_quarantine=has_quarantine,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/ingestion-batches/{batch_id}/quarantine-records",
    response_model=QuarantineRecordListResponse,
)
def get_batch_quarantine_records(
    batch_id: int,
    resource_type: Optional[str] = Query(default=None, max_length=100),
    error_code: Optional[str] = Query(default=None, max_length=100),
    search: Optional[str] = Query(default=None, max_length=255),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    if not db.query(IngestionBatch.id).filter(IngestionBatch.id == batch_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion batch not found")
    return list_quarantine_records(
        db,
        ingestion_batch_id=batch_id,
        resource_type=resource_type,
        error_code=error_code,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/quarantine-records/{record_id}/payload", response_model=QuarantinePayloadOut)
def get_quarantine_payload(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    record = db.query(QuarantineRecord).filter(QuarantineRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quarantine record not found")

    write_audit_event(
        db,
        user=user,
        action="quarantine_payload_viewed",
        resource_type="quarantine_record",
        resource_id=record.id,
        metadata={
            "ingestion_batch_id": record.ingestion_batch_id,
            "resource_type": record.resource_type,
            "source_record_id": record.source_record_id,
            "error_code": record.error_code,
        },
    )
    return record
