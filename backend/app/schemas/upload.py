from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
    onset_date: Optional[datetime]


class ObservationSchema(BaseModel):
    fhir_observation_id: Optional[str]
    patient_reference: Optional[str]
    observation_code: Optional[str]
    observation_name: Optional[str]
    value: Optional[str]
    unit: Optional[str]
    effective_date: Optional[datetime]


class EncounterSchema(BaseModel):
    fhir_encounter_id: Optional[str]
    patient_reference: Optional[str]
    status: Optional[str]
    encounter_class: Optional[str]
    encounter_type: Optional[str]
    period_start: Optional[datetime]
    period_end: Optional[datetime]


class MedicationRequestSchema(BaseModel):
    fhir_medication_request_id: Optional[str]
    patient_reference: Optional[str]
    status: Optional[str]
    intent: Optional[str]
    medication_code: Optional[str]
    medication_name: Optional[str]
    authored_on: Optional[datetime]


class AllergyIntoleranceSchema(BaseModel):
    fhir_allergy_id: Optional[str]
    patient_reference: Optional[str]
    clinical_status: Optional[str]
    verification_status: Optional[str]
    allergy_code: Optional[str]
    allergy_name: Optional[str]
    criticality: Optional[str]
    recorded_date: Optional[datetime]


class ParsedFHIRBundleResponse(BaseModel):
    patient: Optional[PatientSchema]
    conditions: List[ConditionSchema]
    observations: List[ObservationSchema]
    encounters: List[EncounterSchema]
    medication_requests: List[MedicationRequestSchema]
    allergies: List[AllergyIntoleranceSchema]
    resource_counts: Dict[str, int]
    raw_bundle_type: Optional[str]
