from typing import List
from pydantic import BaseModel


class QualityAlert(BaseModel):
    severity: str
    field: str
    message: str


class QualityAlertsResponse(BaseModel):
    patient_id: int
    alerts: List[QualityAlert]
