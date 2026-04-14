from typing import List, Optional
from pydantic import BaseModel


class ConditionOut(BaseModel):
    id: int
    fhir_condition_id: Optional[str]
    condition_code: Optional[str]
    condition_name: Optional[str]
    clinical_status: Optional[str]
    onset_date: Optional[str]

    class Config:
        from_attributes = True


class ObservationOut(BaseModel):
    id: int
    fhir_observation_id: Optional[str]
    observation_code: Optional[str]
    observation_name: Optional[str]
    value: Optional[str]
    unit: Optional[str]
    effective_date: Optional[str]

    class Config:
        from_attributes = True


class PatientOut(BaseModel):
    id: int
    fhir_patient_id: Optional[str]
    full_name: Optional[str]
    gender: Optional[str]
    birth_date: Optional[str]
    conditions: List[ConditionOut]
    observations: List[ObservationOut]

    class Config:
        from_attributes = True
