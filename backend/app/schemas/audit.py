from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    user_id: Optional[int]
    username: Optional[str]
    role: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    patient_id: Optional[int]
    event_timestamp: datetime
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("event_metadata", "metadata"),
        serialization_alias="metadata",
    )


class AuditLogListResponse(BaseModel):
    items: List[AuditLogOut]
    total: int
    limit: int
    offset: int


class DbtAuditRequest(BaseModel):
    status: str = "completed"
    invocation_id: Optional[str] = None
    selected_models: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
