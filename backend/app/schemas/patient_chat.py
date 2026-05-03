from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.ai_insights import InsightCitation


class PatientChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)


class PatientChatResponse(BaseModel):
    patient_id: int
    question: str
    answer: str
    confidence: Literal["high", "medium", "low"]
    generated_by: str
    retrieval_strategy: str
    citations: List[InsightCitation]
    safety_notes: List[str]
    refused: bool = False
    validation_errors: List[str] = []
    llm_used: bool = False
