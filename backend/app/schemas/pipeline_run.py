from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class PipelineRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pipeline_name: str
    run_id: str
    source_system: Optional[str]
    batch_id: Optional[str]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    received_count: int
    accepted_count: int
    rejected_count: int
    duplicate_or_updated_count: int
    error_message: Optional[str]


class PipelineRunListResponse(BaseModel):
    items: List[PipelineRunOut]
    total: int
    limit: int
    offset: int


class PipelineRunMetricsResponse(BaseModel):
    pipeline_name: Optional[str]
    source_system: Optional[str]
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    records_received: int
    records_accepted: int
    records_rejected: int
    average_duration_ms: Optional[float]
    latest_successful_run: Optional[PipelineRunOut]
