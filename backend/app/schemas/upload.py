from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class PatientSchema(BaseModel):
    fhir_patient_id: Optional[str]
    full_name: Optional[str]
    gender: Optional[str]
    birth_date: Optional[str]


class ConditionSchema(BaseModel):
    fhir_condition_id: Optional[str]
    patient_reference: Optional[str]
    condition_code: Optional[str]
    condition_name: Optional[str]
    clinical_status: Optional[str]
    onset_date: Optional[str]


class ObservationSchema(BaseModel):
    fhir_observation_id: Optional[str]
    patient_reference: Optional[str]
    observation_code: Optional[str]
    observation_name: Optional[str]
    value: Optional[str]
    unit: Optional[str]
    effective_date: Optional[str]


class ParsedFHIRBundleResponse(BaseModel):
    patient: Optional[PatientSchema]
    conditions: List[ConditionSchema]
    observations: List[ObservationSchema]
    resource_counts: Dict[str, int]
    raw_bundle_type: Optional[str]
