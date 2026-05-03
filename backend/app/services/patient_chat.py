from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

from app.core.config import settings
from app.services.ai_insights import (
    A1C_CODES,
    BP_CODES,
    DIABETES_TERMS,
    HYPERTENSION_TERMS,
    InsightBuilder,
    _active_conditions,
    _active_medications,
    _format_value,
    _lower,
    _sort_by_date,
)


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
GITHUB_MODELS_CHAT_COMPLETIONS_URL = "https://models.github.ai/inference/chat/completions"
TREATMENT_ADVICE_TERMS = (
    "should i prescribe",
    "should we prescribe",
    "what should i prescribe",
    "what medication should",
    "increase dose",
    "decrease dose",
    "change dose",
    "start medication",
    "stop medication",
    "safe to discharge",
    "diagnose this",
    "what diagnosis should",
    "treatment plan",
)


def answer_patient_question(patient, question: str) -> Dict[str, Any]:
    builder = InsightBuilder(patient)
    normalized_question = question.strip()
    refused = _asks_for_treatment_advice(normalized_question)
    evidence, strategy = _retrieve_evidence(patient, builder, normalized_question)
    citations = _citations_for_evidence(builder.citations, evidence)

    safety_notes = [
        "Answer is limited to retrieved records for this patient.",
        "This assistant supports chart review and does not provide diagnosis or treatment recommendations.",
    ]

    if refused:
        answer = _refusal_answer(evidence)
        return _response(
            patient,
            normalized_question,
            answer,
            "medium" if evidence else "low",
            "ClinSight grounded chart assistant deterministic fallback",
            strategy,
            citations,
            safety_notes,
            refused=True,
        )

    llm_answer = _answer_with_llm(normalized_question, evidence, citations)
    if llm_answer:
        validation_errors = _validate_llm_answer(llm_answer, {citation["id"] for citation in citations})
        if not validation_errors:
            provider_label = _llm_provider_label()
            return _response(
                patient,
                normalized_question,
                llm_answer["answer"],
                llm_answer.get("confidence", "medium"),
                f"{provider_label} with ClinSight grounded retrieval",
                strategy,
                citations,
                safety_notes + llm_answer.get("safety_notes", []),
                llm_used=True,
            )

    return _response(
        patient,
        normalized_question,
        _deterministic_answer(normalized_question, evidence),
        "high" if evidence else "low",
        "ClinSight grounded chart assistant deterministic fallback",
        strategy,
        citations,
        safety_notes,
    )


def _retrieve_evidence(patient, builder: InsightBuilder, question: str) -> Tuple[List[Dict[str, Any]], str]:
    question_text = _lower(question)
    evidence: List[Dict[str, Any]] = []
    strategies = []

    def add(citation_id: str, detail: str):
        if any(item["citation_id"] == citation_id for item in evidence):
            return
        evidence.append({"citation_id": citation_id, "detail": detail})

    add(builder.cite_patient(), _patient_detail(patient))

    if _mentions_any(question_text, DIABETES_TERMS) or "a1c" in question_text or "hba1c" in question_text:
        strategies.append("diabetes_a1c")
        for condition in _matching_conditions(patient.conditions, DIABETES_TERMS):
            add(builder.cite_condition(condition), _condition_detail(condition))
        for observation in _matching_observations(patient.observations, A1C_CODES, ("a1c", "hemoglobin a1c", "hba1c"))[:8]:
            add(builder.cite_observation(observation), _observation_detail(observation))

    if _mentions_any(question_text, HYPERTENSION_TERMS) or "blood pressure" in question_text or " bp" in f" {question_text}":
        strategies.append("hypertension_bp")
        for condition in _matching_conditions(patient.conditions, HYPERTENSION_TERMS):
            add(builder.cite_condition(condition), _condition_detail(condition))
        for observation in _matching_observations(patient.observations, BP_CODES, ("blood pressure", "systolic", "diastolic"))[:10]:
            add(builder.cite_observation(observation), _observation_detail(observation))

    if _mentions_any(question_text, ("medication", "medications", "meds", "drug", "drugs", "prescription")):
        strategies.append("medications")
        for medication in _sort_by_date(_active_medications(patient.medication_requests), "authored_on")[:10]:
            add(builder.cite_medication(medication), _medication_detail(medication))

    if _mentions_any(question_text, ("allergy", "allergies", "allergic")):
        strategies.append("allergies")
        for allergy in _sort_by_date(patient.allergies, "recorded_date")[:10]:
            add(builder.cite_allergy(allergy), _allergy_detail(allergy))

    if _mentions_any(question_text, ("encounter", "encounters", "visit", "visits", "admission", "admissions")):
        strategies.append("encounters")
        for encounter in _sort_by_date(patient.encounters, "period_start")[:8]:
            add(builder.cite_encounter(encounter), _encounter_detail(encounter))

    if _mentions_any(question_text, ("lab", "labs", "observation", "observations", "vital", "vitals", "result", "results", "recent")):
        strategies.append("recent_observations")
        for observation in _sort_by_date(patient.observations, "effective_date")[:10]:
            add(builder.cite_observation(observation), _observation_detail(observation))

    if _mentions_any(question_text, ("condition", "conditions", "problem", "problems", "diagnosis", "diagnoses")):
        strategies.append("conditions")
        for condition in _sort_by_date(_active_conditions(patient.conditions), "onset_date")[:10]:
            add(builder.cite_condition(condition), _condition_detail(condition))

    if len(evidence) == 1:
        strategies.append("general_chart_review")
        for condition in _sort_by_date(_active_conditions(patient.conditions), "onset_date")[:5]:
            add(builder.cite_condition(condition), _condition_detail(condition))
        for observation in _sort_by_date(patient.observations, "effective_date")[:8]:
            add(builder.cite_observation(observation), _observation_detail(observation))
        for medication in _sort_by_date(_active_medications(patient.medication_requests), "authored_on")[:5]:
            add(builder.cite_medication(medication), _medication_detail(medication))
        for allergy in _sort_by_date(patient.allergies, "recorded_date")[:5]:
            add(builder.cite_allergy(allergy), _allergy_detail(allergy))

    return evidence[:24], ", ".join(strategies)


def _answer_with_llm(
    question: str,
    evidence: Sequence[Dict[str, Any]],
    citations: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not evidence:
        return None

    provider = settings.llm_provider.strip().lower()
    if provider == "github":
        return _answer_with_github_models(question, evidence, citations)
    if provider == "openai":
        return _answer_with_openai(question, evidence, citations)
    return None


def _answer_with_github_models(
    question: str,
    evidence: Sequence[Dict[str, Any]],
    citations: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not settings.github_models_token:
        return None

    payload = {
        "model": settings.github_models_model,
        "messages": _chat_messages(question, evidence, citations),
        "temperature": 0,
        "max_tokens": 700,
        "response_format": {
            "type": "json_schema",
            "json_schema": _chat_answer_schema(),
        },
    }

    try:
        response = httpx.post(
            GITHUB_MODELS_CHAT_COMPLETIONS_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {settings.github_models_token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        return None


def _answer_with_openai(
    question: str,
    evidence: Sequence[Dict[str, Any]],
    citations: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not settings.openai_api_key:
        return None

    messages = _chat_messages(question, evidence, citations)
    payload = {
        "model": settings.openai_model,
        "input": [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in messages
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "patient_chart_answer",
                "strict": True,
                "schema": _chat_answer_schema()["schema"],
            }
        },
    }

    try:
        response = httpx.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return json.loads(_output_text(response.json()))
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def _chat_messages(
    question: str,
    evidence: Sequence[Dict[str, Any]],
    citations: Sequence[Dict[str, Any]],
) -> List[Dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are ClinSight's grounded patient chart assistant. Answer only from the provided JSON evidence. "
                "Do not diagnose, prescribe, or recommend treatment changes. If the evidence is insufficient, say so. "
                "Return concise JSON only."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "question": question,
                    "evidence": _evidence_payload(evidence, citations),
                    "required_rules": [
                        "Every factual sentence must be supported by one or more citation IDs from evidence.",
                        "Do not use citation IDs that are absent from evidence.",
                        "Use review-oriented language such as documented, available records, or consider reviewing.",
                        "Do not provide diagnosis, prescribing, dosing, discharge, or treatment recommendations.",
                    ],
                },
                separators=(",", ":"),
            ),
        },
    ]


def _evidence_payload(
    evidence: Sequence[Dict[str, Any]],
    citations: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    citation_lookup = {citation["id"]: citation for citation in citations}
    return [
        {
            "citation_id": item["citation_id"],
            "resource_type": citation_lookup[item["citation_id"]]["resource_type"],
            "label": citation_lookup[item["citation_id"]]["label"],
            "date": citation_lookup[item["citation_id"]]["date"],
            "detail": item["detail"],
            "source_system": citation_lookup[item["citation_id"]].get("source_system"),
            "source_record_id": citation_lookup[item["citation_id"]].get("source_record_id"),
        }
        for item in evidence
        if item["citation_id"] in citation_lookup
    ]


def _chat_answer_schema() -> Dict[str, Any]:
    return {
        "name": "patient_chart_answer",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "answer": {"type": "string"},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "citation_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "safety_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["answer", "confidence", "citation_ids", "safety_notes"],
        },
    }


def _llm_provider_label() -> str:
    provider = settings.llm_provider.strip().lower()
    if provider == "github":
        return f"GitHub Models {settings.github_models_model}"
    if provider == "openai":
        return f"OpenAI {settings.openai_model}"
    return "LLM"


def _validate_llm_answer(answer: Dict[str, Any], citation_ids: set[str]) -> List[str]:
    errors = []
    if not answer.get("answer"):
        errors.append("LLM answer was empty.")
    for citation_id in answer.get("citation_ids", []):
        if citation_id not in citation_ids:
            errors.append(f"Unresolved citation: {citation_id}")
    if _asks_for_treatment_advice(answer.get("answer", "")):
        errors.append("LLM answer included treatment advice language.")
    return errors


def _deterministic_answer(question: str, evidence: Sequence[Dict[str, Any]]) -> str:
    if not evidence:
        return "I could not find structured chart evidence that answers this question in the available patient records."

    evidence_lines = [item["detail"] for item in evidence[1:6] or evidence[:5]]
    if not evidence_lines:
        evidence_lines = [evidence[0]["detail"]]

    return (
        "From the available chart records: "
        + " ".join(evidence_lines)
        + " This answer is limited to the retrieved structured records."
    )


def _refusal_answer(evidence: Sequence[Dict[str, Any]]) -> str:
    if evidence:
        return (
            "I cannot provide diagnosis or treatment recommendations. I can summarize documented chart evidence: "
            + " ".join(item["detail"] for item in evidence[1:5] or evidence[:4])
        )
    return "I cannot provide diagnosis or treatment recommendations, and I did not find enough chart evidence to summarize."


def _response(
    patient,
    question: str,
    answer: str,
    confidence: str,
    generated_by: str,
    retrieval_strategy: str,
    citations: Sequence[Dict[str, Any]],
    safety_notes: Sequence[str],
    refused: bool = False,
    validation_errors: Optional[List[str]] = None,
    llm_used: bool = False,
) -> Dict[str, Any]:
    return {
        "patient_id": patient.id,
        "question": question,
        "answer": answer,
        "confidence": confidence if confidence in {"high", "medium", "low"} else "medium",
        "generated_by": generated_by,
        "retrieval_strategy": retrieval_strategy,
        "citations": list(citations),
        "safety_notes": list(dict.fromkeys(safety_notes)),
        "refused": refused,
        "validation_errors": validation_errors or [],
        "llm_used": llm_used,
    }


def _citations_for_evidence(citations: Sequence[Dict[str, Any]], evidence: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence_ids = {item["citation_id"] for item in evidence}
    return [citation for citation in citations if citation["id"] in evidence_ids]


def _matching_conditions(conditions, terms: Sequence[str]) -> List[Any]:
    return [
        condition
        for condition in _sort_by_date(conditions, "onset_date")
        if _mentions_any(_lower(f"{condition.condition_name} {condition.condition_code}"), terms)
    ]


def _matching_observations(observations, codes: set[str], terms: Sequence[str]) -> List[Any]:
    return [
        observation
        for observation in _sort_by_date(observations, "effective_date")
        if observation.observation_code in codes
        or _mentions_any(_lower(f"{observation.observation_name} {observation.observation_code}"), terms)
    ]


def _patient_detail(patient) -> str:
    return (
        f"Patient {patient.full_name or 'Unnamed patient'} has FHIR ID {patient.fhir_patient_id or 'unavailable'}, "
        f"gender {patient.gender or 'unknown'}, and birth date {patient.birth_date or 'unknown'}."
    )


def _condition_detail(condition) -> str:
    return (
        f"{condition.condition_name or 'Unnamed condition'} is documented with status "
        f"{condition.clinical_status or 'unspecified'}"
        f"{f' and onset {condition.onset_date}' if condition.onset_date else ''}."
    )


def _observation_detail(observation) -> str:
    value = _format_value(observation.value, observation.unit) or "no value"
    return (
        f"{observation.observation_name or 'Unnamed observation'} was recorded as {value}"
        f"{f' on {observation.effective_date}' if observation.effective_date else ''}."
    )


def _medication_detail(medication) -> str:
    return (
        f"{medication.medication_name or 'Unnamed medication request'} has status "
        f"{medication.status or 'unspecified'}"
        f"{f' and was authored on {medication.authored_on}' if medication.authored_on else ''}."
    )


def _allergy_detail(allergy) -> str:
    return (
        f"{allergy.allergy_name or 'Unnamed allergy'} is documented with criticality "
        f"{allergy.criticality or 'unspecified'} and clinical status {allergy.clinical_status or 'unspecified'}."
    )


def _encounter_detail(encounter) -> str:
    return (
        f"{encounter.encounter_type or 'Encounter'} has status {encounter.status or 'unspecified'}"
        f"{f' from {encounter.period_start}' if encounter.period_start else ''}"
        f"{f' to {encounter.period_end}' if encounter.period_end else ''}."
    )


def _asks_for_treatment_advice(text: str) -> bool:
    lowered = _lower(text)
    return any(term in lowered for term in TREATMENT_ADVICE_TERMS)


def _mentions_any(text: str, terms: Sequence[str]) -> bool:
    return any(term in text for term in terms)


def _output_text(payload: Dict[str, Any]) -> str:
    if payload.get("output_text"):
        return payload["output_text"]
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
    raise KeyError("No output text in OpenAI response")
