from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.ingestion_batch import IngestionBatch
from app.models.quarantine_record import QuarantineRecord
from app.models.source_system import SourceSystem


def list_ingestion_batches(
    db: Session,
    *,
    status: Optional[str],
    source_system: Optional[str],
    has_quarantine: Optional[bool],
    limit: int,
    offset: int,
):
    quarantine_count = (
        db.query(func.count(QuarantineRecord.id))
        .filter(QuarantineRecord.ingestion_batch_id == IngestionBatch.id)
        .correlate(IngestionBatch)
        .scalar_subquery()
    )
    query = db.query(IngestionBatch, SourceSystem, quarantine_count.label("quarantine_count")).join(
        SourceSystem,
        SourceSystem.id == IngestionBatch.source_system_id,
    )
    if status:
        query = query.filter(IngestionBatch.status == status)
    if source_system:
        query = query.filter(SourceSystem.name.ilike(f"%{source_system}%"))
    if has_quarantine is True:
        query = query.filter(quarantine_count > 0)
    elif has_quarantine is False:
        query = query.filter(quarantine_count == 0)

    total = query.count()
    rows = (
        query.order_by(IngestionBatch.started_at.desc(), IngestionBatch.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = [
        {
            "id": batch.id,
            "source_system_id": batch.source_system_id,
            "source_system_name": source.name,
            "source_system_type": source.system_type,
            "ingestion_type": batch.ingestion_type,
            "filename": batch.filename,
            "status": batch.status,
            "record_count": batch.record_count,
            "accepted_count": batch.accepted_count,
            "rejected_count": batch.rejected_count,
            "quarantine_count": count,
            "error_message": batch.error_message,
            "started_at": batch.started_at,
            "completed_at": batch.completed_at,
        }
        for batch, source, count in rows
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def list_quarantine_records(
    db: Session,
    *,
    ingestion_batch_id: int,
    resource_type: Optional[str],
    error_code: Optional[str],
    search: Optional[str],
    limit: int,
    offset: int,
):
    query = db.query(QuarantineRecord).filter(
        QuarantineRecord.ingestion_batch_id == ingestion_batch_id
    )
    if resource_type:
        query = query.filter(QuarantineRecord.resource_type == resource_type)
    if error_code:
        query = query.filter(QuarantineRecord.error_code == error_code)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                QuarantineRecord.source_record_id.ilike(pattern),
                QuarantineRecord.error_message.ilike(pattern),
            )
        )

    total = query.count()
    items = (
        query.order_by(QuarantineRecord.created_at.desc(), QuarantineRecord.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}
