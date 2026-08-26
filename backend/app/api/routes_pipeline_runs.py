from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.pipeline_run import PipelineRunListResponse, PipelineRunMetricsResponse
from app.services.auth import require_roles
from app.services.pipeline_runs import list_pipeline_runs, summarize_pipeline_runs


router = APIRouter()


@router.get("/pipeline-runs", response_model=PipelineRunListResponse)
def get_pipeline_runs(
    pipeline_name: Optional[str] = Query(default=None, max_length=100),
    status: Optional[str] = Query(default=None, max_length=50),
    source_system: Optional[str] = Query(default=None, max_length=255),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    return list_pipeline_runs(
        db,
        pipeline_name=pipeline_name,
        status=status,
        source_system=source_system,
        limit=limit,
        offset=offset,
    )


@router.get("/pipeline-runs/metrics", response_model=PipelineRunMetricsResponse)
def get_pipeline_run_metrics(
    pipeline_name: Optional[str] = Query(default=None, max_length=100),
    source_system: Optional[str] = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    return summarize_pipeline_runs(
        db,
        pipeline_name=pipeline_name,
        source_system=source_system,
    )
