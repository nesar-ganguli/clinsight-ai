from typing import List, Optional

from pydantic import BaseModel


class ExternalFhirPatientSummary(BaseModel):
    id: str
    full_name: Optional[str]
    gender: Optional[str]
    birth_date: Optional[str]


class ExternalFhirPatientListResponse(BaseModel):
    items: List[ExternalFhirPatientSummary]
    total: int
    source_system: str
    fhir_base_url: str


class ExternalFhirImportResponse(BaseModel):
    message: str
    patient_id: int
    import_mode: str
    resource_counts: dict[str, int]
    source_system: str
    external_patient_id: str
