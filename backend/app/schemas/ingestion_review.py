from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class IngestionBatchOut(BaseModel):
    id: int
    source_system_id: int
    source_system_name: str
    source_system_type: str
    ingestion_type: str
    filename: Optional[str]
    status: str
    record_count: int
    accepted_count: int
    rejected_count: int
    quarantine_count: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]


class IngestionBatchListResponse(BaseModel):
    items: List[IngestionBatchOut]
    total: int
    limit: int
    offset: int


class QuarantineRecordSummaryOut(BaseModel):
    id: int
    ingestion_batch_id: int
    source_system_id: int
    resource_type: str
    source_record_id: Optional[str]
    error_code: str
    error_message: str
    created_at: datetime


class QuarantineRecordListResponse(BaseModel):
    items: List[QuarantineRecordSummaryOut]
    total: int
    limit: int
    offset: int


class QuarantinePayloadOut(BaseModel):
    id: int
    ingestion_batch_id: int
    raw_payload: Any
