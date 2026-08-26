import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.pipeline_run import PipelineRun


logger = logging.getLogger(__name__)
PIPELINE_STATUS_PROCESSING = "processing"
PIPELINE_STATUS_SUCCESS = "success"
PIPELINE_STATUS_FAILED = "failed"


def start_pipeline_run(
    db: Session,
    *,
    pipeline_name: str,
    run_id: str,
    source_system: Optional[str],
    batch_id: Optional[str],
    received_count: int = 0,
    commit: bool = True,
) -> PipelineRun:
    pipeline_run = _find_pipeline_run(db, pipeline_name, run_id)
    started_at = datetime.now(timezone.utc)
    if pipeline_run is None:
        pipeline_run = PipelineRun(
            pipeline_name=pipeline_name,
            run_id=run_id,
        )
        db.add(pipeline_run)

    pipeline_run.source_system = source_system
    pipeline_run.batch_id = batch_id
    pipeline_run.status = PIPELINE_STATUS_PROCESSING
    pipeline_run.started_at = started_at
    pipeline_run.completed_at = None
    pipeline_run.duration_ms = None
    pipeline_run.received_count = received_count
    pipeline_run.accepted_count = 0
    pipeline_run.rejected_count = 0
    pipeline_run.duplicate_or_updated_count = 0
    pipeline_run.error_message = None
    _save(db, pipeline_run, commit)
    log_pipeline_event(
        "pipeline_started",
        pipeline_run,
        received_count=received_count,
    )
    return pipeline_run


def complete_pipeline_run(
    db: Session,
    *,
    pipeline_name: str,
    run_id: str,
    received_count: int,
    accepted_count: int,
    rejected_count: int,
    duplicate_or_updated_count: int = 0,
    commit: bool = True,
) -> PipelineRun:
    pipeline_run = _require_pipeline_run(db, pipeline_name, run_id)
    completed_at = datetime.now(timezone.utc)
    pipeline_run.status = PIPELINE_STATUS_SUCCESS
    pipeline_run.completed_at = completed_at
    pipeline_run.duration_ms = _duration_ms(pipeline_run.started_at, completed_at)
    pipeline_run.received_count = received_count
    pipeline_run.accepted_count = accepted_count
    pipeline_run.rejected_count = rejected_count
    pipeline_run.duplicate_or_updated_count = duplicate_or_updated_count
    pipeline_run.error_message = None
    _save(db, pipeline_run, commit)
    log_pipeline_event(
        "pipeline_succeeded",
        pipeline_run,
        received_count=received_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        duplicate_or_updated_count=duplicate_or_updated_count,
    )
    return pipeline_run


def fail_pipeline_run(
    db: Session,
    *,
    pipeline_name: str,
    run_id: str,
    error_message: str,
    source_system: Optional[str] = None,
    batch_id: Optional[str] = None,
    received_count: Optional[int] = None,
    rejected_count: Optional[int] = None,
    commit: bool = True,
) -> PipelineRun:
    pipeline_run = _find_pipeline_run(db, pipeline_name, run_id)
    if pipeline_run is None:
        pipeline_run = PipelineRun(
            pipeline_name=pipeline_name,
            run_id=run_id,
            source_system=source_system,
            batch_id=batch_id,
            started_at=datetime.now(timezone.utc),
        )
        db.add(pipeline_run)

    completed_at = datetime.now(timezone.utc)
    pipeline_run.status = PIPELINE_STATUS_FAILED
    pipeline_run.completed_at = completed_at
    pipeline_run.duration_ms = _duration_ms(pipeline_run.started_at, completed_at)
    if source_system is not None:
        pipeline_run.source_system = source_system
    if batch_id is not None:
        pipeline_run.batch_id = batch_id
    if received_count is not None:
        pipeline_run.received_count = received_count
    if rejected_count is not None:
        pipeline_run.rejected_count = rejected_count
    pipeline_run.error_message = _sanitize_error_message(error_message)
    _save(db, pipeline_run, commit)
    log_pipeline_event("pipeline_failed", pipeline_run)
    return pipeline_run


def list_pipeline_runs(
    db: Session,
    *,
    pipeline_name: Optional[str] = None,
    status: Optional[str] = None,
    source_system: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    query = db.query(PipelineRun)
    if pipeline_name:
        query = query.filter(PipelineRun.pipeline_name == pipeline_name)
    if status:
        query = query.filter(PipelineRun.status == status)
    if source_system:
        query = query.filter(PipelineRun.source_system == source_system)

    return {
        "items": (
            query.order_by(PipelineRun.started_at.desc(), PipelineRun.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        ),
        "total": query.count(),
        "limit": limit,
        "offset": offset,
    }


def summarize_pipeline_runs(
    db: Session,
    *,
    pipeline_name: Optional[str] = None,
    source_system: Optional[str] = None,
) -> Dict[str, Any]:
    query = db.query(PipelineRun)
    if pipeline_name:
        query = query.filter(PipelineRun.pipeline_name == pipeline_name)
    if source_system:
        query = query.filter(PipelineRun.source_system == source_system)

    total_runs = query.count()
    successful_runs = query.filter(PipelineRun.status == PIPELINE_STATUS_SUCCESS).count()
    failed_runs = query.filter(PipelineRun.status == PIPELINE_STATUS_FAILED).count()
    terminal_runs = successful_runs + failed_runs
    aggregates = query.with_entities(
        func.coalesce(func.sum(PipelineRun.received_count), 0),
        func.coalesce(func.sum(PipelineRun.accepted_count), 0),
        func.coalesce(func.sum(PipelineRun.rejected_count), 0),
        func.avg(PipelineRun.duration_ms),
    ).one()
    latest_successful_run = (
        query.filter(PipelineRun.status == PIPELINE_STATUS_SUCCESS)
        .order_by(PipelineRun.completed_at.desc(), PipelineRun.id.desc())
        .first()
    )

    return {
        "pipeline_name": pipeline_name,
        "source_system": source_system,
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "success_rate": round(successful_runs / terminal_runs, 4) if terminal_runs else 0.0,
        "records_received": int(aggregates[0]),
        "records_accepted": int(aggregates[1]),
        "records_rejected": int(aggregates[2]),
        "average_duration_ms": round(float(aggregates[3]), 2) if aggregates[3] is not None else None,
        "latest_successful_run": latest_successful_run,
    }


def log_stage_event(
    *,
    pipeline_name: str,
    run_id: str,
    batch_id: Optional[str],
    stage: str,
    status: str,
    duration_ms: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    payload = {
        "event": "pipeline_stage",
        "pipeline_name": pipeline_name,
        "run_id": run_id,
        "batch_id": batch_id,
        "stage": stage,
        "status": status,
        "duration_ms": duration_ms,
    }
    if error_message:
        payload["error_message"] = _sanitize_error_message(error_message)
    logger.info(json.dumps(payload, sort_keys=True))


def log_pipeline_event(event: str, pipeline_run: PipelineRun, **counts: int) -> None:
    payload = {
        "event": event,
        "pipeline_name": pipeline_run.pipeline_name,
        "run_id": pipeline_run.run_id,
        "source_system": pipeline_run.source_system,
        "batch_id": pipeline_run.batch_id,
        "status": pipeline_run.status,
        "duration_ms": pipeline_run.duration_ms,
        "received_count": pipeline_run.received_count,
        "accepted_count": pipeline_run.accepted_count,
        "rejected_count": pipeline_run.rejected_count,
        "duplicate_or_updated_count": pipeline_run.duplicate_or_updated_count,
        **counts,
    }
    logger.info(json.dumps(payload, sort_keys=True))


def _find_pipeline_run(db: Session, pipeline_name: str, run_id: str) -> Optional[PipelineRun]:
    return (
        db.query(PipelineRun)
        .filter(
            PipelineRun.pipeline_name == pipeline_name,
            PipelineRun.run_id == run_id,
        )
        .first()
    )


def _require_pipeline_run(db: Session, pipeline_name: str, run_id: str) -> PipelineRun:
    pipeline_run = _find_pipeline_run(db, pipeline_name, run_id)
    if pipeline_run is None:
        raise RuntimeError(f"Pipeline run {pipeline_name}/{run_id} was not found")
    return pipeline_run


def _save(db: Session, pipeline_run: PipelineRun, commit: bool) -> None:
    if commit:
        db.commit()
        db.refresh(pipeline_run)
    else:
        db.flush()


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return max(0, int((completed_at - started_at).total_seconds() * 1000))


def _sanitize_error_message(error_message: str) -> str:
    normalized = " ".join(error_message.split())
    return normalized[:1000] or "Pipeline failed"
