from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fhir_condition_id: Optional[str]
    condition_code: Optional[str]
    condition_name: Optional[str]
    clinical_status: Optional[str]
    onset_date: Optional[str]


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fhir_observation_id: Optional[str]
    observation_code: Optional[str]
    observation_name: Optional[str]
    value: Optional[str]
    unit: Optional[str]
    effective_date: Optional[str]


class EncounterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fhir_encounter_id: Optional[str]
    status: Optional[str]
    encounter_class: Optional[str]
    encounter_type: Optional[str]
    period_start: Optional[str]
    period_end: Optional[str]


class MedicationRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fhir_medication_request_id: Optional[str]
    status: Optional[str]
    intent: Optional[str]
    medication_code: Optional[str]
    medication_name: Optional[str]
    authored_on: Optional[str]


class AllergyIntoleranceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fhir_allergy_id: Optional[str]
    clinical_status: Optional[str]
    verification_status: Optional[str]
    allergy_code: Optional[str]
    allergy_name: Optional[str]
    criticality: Optional[str]
    recorded_date: Optional[str]


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fhir_patient_id: Optional[str]
    full_name: Optional[str]
    gender: Optional[str]
    birth_date: Optional[str]
    conditions: List[ConditionOut]
    observations: List[ObservationOut]
    encounters: List[EncounterOut]
    medication_requests: List[MedicationRequestOut]
    allergies: List[AllergyIntoleranceOut]


class PatientSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fhir_patient_id: Optional[str]
    full_name: Optional[str]
    gender: Optional[str]
    birth_date: Optional[str]


class PatientListResponse(BaseModel):
    items: List[PatientSummaryOut]
    total: int
    limit: int
    offset: int
