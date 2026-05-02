from typing import List, Literal, Optional

from pydantic import BaseModel


class InsightCitation(BaseModel):
    id: str
    resource_type: str
    record_id: int
    fhir_id: Optional[str]
    label: str
    date: Optional[str]
    excerpt: str
    source_type: Optional[str] = None
    source_system: Optional[str] = None
    source_record_id: Optional[str] = None
    ingestion_batch_id: Optional[str] = None
    transformed_at: Optional[str] = None


class SupportedClaim(BaseModel):
    id: str
    text: str
    citation_ids: List[str]


class SummarySection(BaseModel):
    title: str
    claims: List[SupportedClaim]


class ChartInconsistency(BaseModel):
    code: str
    severity: Literal["critical", "warning", "info"]
    title: str
    explanation: str
    citation_ids: List[str]


class CareGapSuggestion(BaseModel):
    code: str
    priority: Literal["high", "medium", "low"]
    title: str
    recommendation: str
    rationale: str
    citation_ids: List[str]


class InsightEvaluation(BaseModel):
    grounded_claims: int
    unsupported_claims: int
    unresolved_citations: int
    source_coverage: float
    hallucination_risk: Literal["low", "medium", "high"]
    checks: List[str]


class PatientAiInsightsResponse(BaseModel):
    patient_id: int
    generated_by: str
    disclaimer: str
    summary_sections: List[SummarySection]
    inconsistencies: List[ChartInconsistency]
    care_gaps: List[CareGapSuggestion]
    citations: List[InsightCitation]
    evaluation: InsightEvaluation
