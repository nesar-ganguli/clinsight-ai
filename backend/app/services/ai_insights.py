from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from app.services.quality_checker import run_quality_checks


DIABETES_CODES = {"44054006", "73211009", "46635009"}
DIABETES_TERMS = ("diabetes", "diabetic")
HYPERTENSION_CODES = {"38341003", "59621000"}
HYPERTENSION_TERMS = ("hypertension", "high blood pressure")
A1C_CODES = {"4548-4", "17856-6", "41995-2"}
BP_CODES = {"85354-9", "8480-6", "8462-4"}
ACTIVE_STATUS_VALUES = {"active", "recurrence", "relapse"}
INACTIVE_STATUS_VALUES = {"inactive", "resolved", "remission"}
ACTIVE_MEDICATION_STATUSES = {"active", "on-hold", "draft", "unknown"}


class InsightBuilder:
    def __init__(self, patient):
        self.patient = patient
        self._citations: Dict[str, Dict[str, Any]] = {}

    @property
    def citations(self) -> List[Dict[str, Any]]:
        return list(self._citations.values())

    def cite_patient(self) -> str:
        label = self.patient.full_name or "Unnamed patient"
        excerpt = ", ".join(
            part
            for part in [
                f"FHIR ID {self.patient.fhir_patient_id}" if self.patient.fhir_patient_id else None,
                f"gender {self.patient.gender}" if self.patient.gender else None,
                f"birth date {self.patient.birth_date}" if self.patient.birth_date else None,
            ]
            if part
        ) or "Patient demographics are partially populated."

        return self._add_citation(
            resource_type="Patient",
            record_id=self.patient.id,
            fhir_id=self.patient.fhir_patient_id,
            label=label,
            date=self.patient.birth_date,
            excerpt=excerpt,
        )

    def cite_condition(self, condition) -> str:
        return self._add_citation(
            resource_type="Condition",
            record_id=condition.id,
            fhir_id=condition.fhir_condition_id,
            label=condition.condition_name or "Unnamed condition",
            date=condition.onset_date,
            excerpt=self._join_excerpt(
                condition.condition_name,
                condition.condition_code,
                f"status {condition.clinical_status}" if condition.clinical_status else None,
                f"onset {condition.onset_date}" if condition.onset_date else None,
            ),
        )

    def cite_observation(self, observation) -> str:
        value = _format_value(observation.value, observation.unit)
        return self._add_citation(
            resource_type="Observation",
            record_id=observation.id,
            fhir_id=observation.fhir_observation_id,
            label=observation.observation_name or "Unnamed observation",
            date=observation.effective_date,
            excerpt=self._join_excerpt(
                observation.observation_name,
                observation.observation_code,
                value,
                f"effective {observation.effective_date}" if observation.effective_date else None,
            ),
        )

    def cite_encounter(self, encounter) -> str:
        return self._add_citation(
            resource_type="Encounter",
            record_id=encounter.id,
            fhir_id=encounter.fhir_encounter_id,
            label=encounter.encounter_type or "Encounter",
            date=encounter.period_start,
            excerpt=self._join_excerpt(
                encounter.encounter_type,
                f"status {encounter.status}" if encounter.status else None,
                f"class {encounter.encounter_class}" if encounter.encounter_class else None,
                f"start {encounter.period_start}" if encounter.period_start else None,
                f"end {encounter.period_end}" if encounter.period_end else None,
            ),
        )

    def cite_medication(self, medication) -> str:
        return self._add_citation(
            resource_type="MedicationRequest",
            record_id=medication.id,
            fhir_id=medication.fhir_medication_request_id,
            label=medication.medication_name or "Unnamed medication request",
            date=medication.authored_on,
            excerpt=self._join_excerpt(
                medication.medication_name,
                medication.medication_code,
                f"status {medication.status}" if medication.status else None,
                f"intent {medication.intent}" if medication.intent else None,
                f"authored {medication.authored_on}" if medication.authored_on else None,
            ),
        )

    def cite_allergy(self, allergy) -> str:
        return self._add_citation(
            resource_type="AllergyIntolerance",
            record_id=allergy.id,
            fhir_id=allergy.fhir_allergy_id,
            label=allergy.allergy_name or "Unnamed allergy",
            date=allergy.recorded_date,
            excerpt=self._join_excerpt(
                allergy.allergy_name,
                allergy.allergy_code,
                f"clinical {allergy.clinical_status}" if allergy.clinical_status else None,
                f"verification {allergy.verification_status}" if allergy.verification_status else None,
                f"criticality {allergy.criticality}" if allergy.criticality else None,
            ),
        )

    def _add_citation(
        self,
        resource_type: str,
        record_id: int,
        fhir_id: Optional[str],
        label: str,
        date: Optional[str],
        excerpt: str,
    ) -> str:
        citation_id = f"{resource_type}:{record_id}"
        if citation_id not in self._citations:
            self._citations[citation_id] = {
                "id": citation_id,
                "resource_type": resource_type,
                "record_id": record_id,
                "fhir_id": fhir_id,
                "label": label,
                "date": date,
                "excerpt": excerpt,
            }
        return citation_id

    def _join_excerpt(self, *parts: Optional[str]) -> str:
        values = [str(part).strip() for part in parts if part is not None and str(part).strip()]
        return " | ".join(values) if values else "Record has limited structured detail."


def build_patient_ai_insights(patient) -> Dict[str, Any]:
    builder = InsightBuilder(patient)
    summary_sections = _build_summary_sections(patient, builder)
    inconsistencies = _detect_inconsistencies(patient, builder)
    care_gaps = _suggest_care_gaps(patient, builder)
    citations = builder.citations
    evaluation = _evaluate_report(summary_sections, inconsistencies, care_gaps, citations, patient)

    return {
        "patient_id": patient.id,
        "generated_by": "ClinSight grounded insight rules v1",
        "disclaimer": "AI-assisted chart review. Verify all findings against the source record before clinical use.",
        "summary_sections": summary_sections,
        "inconsistencies": inconsistencies,
        "care_gaps": care_gaps,
        "citations": citations,
        "evaluation": evaluation,
    }


def _build_summary_sections(patient, builder: InsightBuilder) -> List[Dict[str, Any]]:
    sections = [
        {
            "title": "Patient overview",
            "claims": [
                _claim(
                    "overview-demographics",
                    _overview_text(patient),
                    [builder.cite_patient()],
                ),
                _claim(
                    "overview-chart-density",
                    (
                        f"The chart contains {len(patient.conditions)} condition(s), "
                        f"{len(patient.observations)} observation(s), {len(patient.encounters)} encounter(s), "
                        f"{len(patient.medication_requests)} medication request(s), and {len(patient.allergies)} allergy record(s)."
                    ),
                    [builder.cite_patient()],
                ),
            ],
        }
    ]

    active_conditions = _active_conditions(patient.conditions)
    if active_conditions:
        condition_claims = []
        for index, condition in enumerate(_sort_by_date(active_conditions, "onset_date")[:5], start=1):
            status = condition.clinical_status or "unspecified status"
            onset = f" with onset {condition.onset_date}" if condition.onset_date else ""
            condition_claims.append(
                _claim(
                    f"condition-{index}",
                    f"{condition.condition_name or 'Unnamed condition'} is documented as {status}{onset}.",
                    [builder.cite_condition(condition)],
                )
            )
        sections.append({"title": "Problem list", "claims": condition_claims})
    else:
        sections.append(
            {
                "title": "Problem list",
                "claims": [
                    _claim(
                        "condition-none",
                        "No active conditions are documented in the structured problem list.",
                        [builder.cite_patient()],
                    )
                ],
            }
        )

    latest_observations = _sort_by_date(patient.observations, "effective_date")[:5]
    if latest_observations:
        observation_claims = []
        for index, observation in enumerate(latest_observations, start=1):
            value = _format_value(observation.value, observation.unit) or "no value"
            date = f" on {observation.effective_date}" if observation.effective_date else ""
            observation_claims.append(
                _claim(
                    f"observation-{index}",
                    f"{observation.observation_name or 'Unnamed observation'} was recorded as {value}{date}.",
                    [builder.cite_observation(observation)],
                )
            )
        sections.append({"title": "Recent observations", "claims": observation_claims})

    medications = _active_medications(patient.medication_requests)
    if medications:
        medication_claims = []
        for index, medication in enumerate(_sort_by_date(medications, "authored_on")[:5], start=1):
            authored = f" authored on {medication.authored_on}" if medication.authored_on else ""
            medication_claims.append(
                _claim(
                    f"medication-{index}",
                    f"{medication.medication_name or 'Unnamed medication request'} has status {medication.status or 'unspecified'}{authored}.",
                    [builder.cite_medication(medication)],
                )
            )
        sections.append({"title": "Medication activity", "claims": medication_claims})
    else:
        sections.append(
            {
                "title": "Medication activity",
                "claims": [
                    _claim(
                        "medication-none",
                        "No active medication requests are documented in the structured medication list.",
                        [builder.cite_patient()],
                    )
                ],
            }
        )

    if patient.allergies:
        allergy_claims = []
        for index, allergy in enumerate(_sort_by_date(patient.allergies, "recorded_date")[:5], start=1):
            criticality = f" with {allergy.criticality} criticality" if allergy.criticality else ""
            allergy_claims.append(
                _claim(
                    f"allergy-{index}",
                    f"{allergy.allergy_name or 'Unnamed allergy'} is documented{criticality}.",
                    [builder.cite_allergy(allergy)],
                )
            )
        sections.append({"title": "Allergies", "claims": allergy_claims})

    return sections


def _detect_inconsistencies(patient, builder: InsightBuilder) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    for encounter in patient.encounters:
        if _is_after(encounter.period_start, encounter.period_end):
            findings.append(
                {
                    "code": "encounter_end_before_start",
                    "severity": "warning",
                    "title": "Encounter end precedes start",
                    "explanation": "The encounter period end is earlier than the recorded start, which can distort timelines and duration-based review.",
                    "citation_ids": [builder.cite_encounter(encounter)],
                }
            )

    by_observation_key: Dict[tuple, List[Any]] = defaultdict(list)
    for observation in patient.observations:
        if observation.observation_code and observation.effective_date:
            by_observation_key[(observation.observation_code, observation.effective_date)].append(observation)

    for observations in by_observation_key.values():
        values = {_normalize_value(observation.value, observation.unit) for observation in observations}
        values.discard("")
        if len(values) > 1:
            label = observations[0].observation_name or observations[0].observation_code
            findings.append(
                {
                    "code": "conflicting_observation_values",
                    "severity": "warning",
                    "title": "Conflicting observation values",
                    "explanation": f"{label} has multiple different values recorded for the same effective date.",
                    "citation_ids": [builder.cite_observation(observation) for observation in observations],
                }
            )

    active_conditions = {
        (condition.condition_code or _lower(condition.condition_name))
        for condition in patient.conditions
        if _lower(condition.clinical_status) in ACTIVE_STATUS_VALUES
    }
    inactive_conditions = {
        (condition.condition_code or _lower(condition.condition_name))
        for condition in patient.conditions
        if _lower(condition.clinical_status) in INACTIVE_STATUS_VALUES
    }
    overlapping_condition_keys = {key for key in active_conditions.intersection(inactive_conditions) if key}

    for condition_key in sorted(overlapping_condition_keys):
        matching = [
            condition
            for condition in patient.conditions
            if (condition.condition_code or _lower(condition.condition_name)) == condition_key
        ]
        findings.append(
            {
                "code": "condition_status_conflict",
                "severity": "warning",
                "title": "Condition has conflicting statuses",
                "explanation": "The same condition appears with both active and inactive/resolved status values.",
                "citation_ids": [builder.cite_condition(condition) for condition in matching],
            }
        )

    medication_names = defaultdict(set)
    medication_records = defaultdict(list)
    for medication in patient.medication_requests:
        normalized_name = _lower(medication.medication_name)
        if normalized_name:
            medication_names[normalized_name].add(_lower(medication.status) or "unspecified")
            medication_records[normalized_name].append(medication)

    for medication_name, statuses in medication_names.items():
        if "active" in statuses and "stopped" in statuses:
            findings.append(
                {
                    "code": "medication_active_and_stopped",
                    "severity": "warning",
                    "title": "Medication has active and stopped statuses",
                    "explanation": f"{medication_name} appears as both active and stopped in medication requests.",
                    "citation_ids": [builder.cite_medication(medication) for medication in medication_records[medication_name]],
                }
            )

    if not findings:
        findings.append(
            {
                "code": "no_inconsistencies_detected",
                "severity": "info",
                "title": "No structured inconsistencies detected",
                "explanation": "The current rule set did not find date conflicts, duplicate observation conflicts, or status contradictions.",
                "citation_ids": [builder.cite_patient()],
            }
        )

    return findings


def _suggest_care_gaps(patient, builder: InsightBuilder) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    diabetes_conditions = [condition for condition in patient.conditions if _matches_condition(condition, DIABETES_CODES, DIABETES_TERMS)]
    hypertension_conditions = [condition for condition in patient.conditions if _matches_condition(condition, HYPERTENSION_CODES, HYPERTENSION_TERMS)]

    if diabetes_conditions and not _has_observation(patient.observations, A1C_CODES, ("a1c", "hemoglobin a1c", "hba1c")):
        suggestions.append(
            {
                "code": "diabetes_a1c_gap",
                "priority": "high",
                "title": "Review A1c monitoring",
                "recommendation": "Consider checking whether hemoglobin A1c monitoring is due or missing from the imported record.",
                "rationale": "Diabetes is documented, but no structured A1c observation was found in this chart extract.",
                "citation_ids": [builder.cite_condition(condition) for condition in diabetes_conditions[:3]],
            }
        )

    if hypertension_conditions and not _has_observation(patient.observations, BP_CODES, ("blood pressure", "systolic", "diastolic")):
        suggestions.append(
            {
                "code": "hypertension_bp_gap",
                "priority": "high",
                "title": "Review blood pressure monitoring",
                "recommendation": "Consider checking whether recent blood pressure data is missing from the imported record.",
                "rationale": "Hypertension is documented, but no structured blood pressure observation was found.",
                "citation_ids": [builder.cite_condition(condition) for condition in hypertension_conditions[:3]],
            }
        )

    active_conditions = _active_conditions(patient.conditions)
    if active_conditions and not patient.encounters:
        suggestions.append(
            {
                "code": "active_conditions_without_encounter_context",
                "priority": "medium",
                "title": "Add encounter context",
                "recommendation": "Review whether encounters are missing for this patient before relying on chronology or acuity.",
                "rationale": "The chart includes active conditions but no structured encounters.",
                "citation_ids": [builder.cite_condition(condition) for condition in active_conditions[:3]],
            }
        )

    if active_conditions and not _active_medications(patient.medication_requests):
        suggestions.append(
            {
                "code": "active_conditions_without_medications",
                "priority": "medium",
                "title": "Review medication reconciliation",
                "recommendation": "Confirm whether the patient has no active medications or whether medication requests are absent from the import.",
                "rationale": "The chart includes active conditions but no active structured medication requests.",
                "citation_ids": [builder.cite_condition(condition) for condition in active_conditions[:3]],
            }
        )

    if not patient.allergies:
        suggestions.append(
            {
                "code": "allergy_status_unknown",
                "priority": "low",
                "title": "Confirm allergy status",
                "recommendation": "Confirm whether the absence of allergy records means no known allergies or incomplete data capture.",
                "rationale": "No allergy records were found in the imported chart.",
                "citation_ids": [builder.cite_patient()],
            }
        )

    quality_alerts = run_quality_checks(patient)
    warning_alerts = [alert for alert in quality_alerts if alert["severity"] in {"critical", "warning"}]
    if warning_alerts:
        suggestions.append(
            {
                "code": "quality_review_needed",
                "priority": "medium",
                "title": "Resolve data quality warnings",
                "recommendation": "Address required demographics and missing clinical values before using the summary for handoff.",
                "rationale": f"{len(warning_alerts)} warning-level chart quality issue(s) were detected.",
                "citation_ids": [builder.cite_patient()],
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "code": "no_care_gaps_detected",
                "priority": "low",
                "title": "No rule-based care gaps detected",
                "recommendation": "Continue routine clinical review; no supported care gap suggestion was triggered by this rule set.",
                "rationale": "Available structured records satisfied the currently implemented care gap checks.",
                "citation_ids": [builder.cite_patient()],
            }
        )

    return suggestions


def _evaluate_report(
    summary_sections: Sequence[Dict[str, Any]],
    inconsistencies: Sequence[Dict[str, Any]],
    care_gaps: Sequence[Dict[str, Any]],
    citations: Sequence[Dict[str, Any]],
    patient,
) -> Dict[str, Any]:
    citation_ids = {citation["id"] for citation in citations}
    claims = [claim for section in summary_sections for claim in section["claims"]]
    findings = [*inconsistencies, *care_gaps]
    supported_claims = sum(1 for claim in claims if claim["citation_ids"])
    unsupported_claims = sum(1 for claim in claims if not claim["citation_ids"])
    unresolved_citations = 0

    for claim in claims:
        unresolved_citations += sum(1 for citation_id in claim["citation_ids"] if citation_id not in citation_ids)
    for finding in findings:
        unresolved_citations += sum(1 for citation_id in finding["citation_ids"] if citation_id not in citation_ids)

    available_source_count = _source_record_count(patient)
    cited_source_count = len({(citation["resource_type"], citation["record_id"]) for citation in citations})
    source_coverage = round(cited_source_count / available_source_count, 2) if available_source_count else 1.0
    hallucination_risk = "low"
    if unsupported_claims or unresolved_citations:
        hallucination_risk = "high"
    elif source_coverage < 0.25:
        hallucination_risk = "medium"

    checks = [
        "Every summary claim must include at least one citation.",
        "Every inconsistency and care gap must cite a persisted source record.",
        "Citation IDs must resolve to the citation table returned with the report.",
        "Care gap recommendations are rule-triggered from documented conditions and observed missing records.",
    ]

    return {
        "grounded_claims": supported_claims,
        "unsupported_claims": unsupported_claims,
        "unresolved_citations": unresolved_citations,
        "source_coverage": source_coverage,
        "hallucination_risk": hallucination_risk,
        "checks": checks,
    }


def _claim(claim_id: str, text: str, citation_ids: List[str]) -> Dict[str, Any]:
    return {
        "id": claim_id,
        "text": text,
        "citation_ids": citation_ids,
    }


def _overview_text(patient) -> str:
    name = patient.full_name or "This patient"
    demographics = []
    if patient.gender:
        demographics.append(patient.gender)
    if patient.birth_date:
        demographics.append(f"born {patient.birth_date}")
    if demographics:
        return f"{name} is documented as {', '.join(demographics)}."
    return f"{name} has limited structured demographics in the imported chart."


def _active_conditions(conditions: Iterable[Any]) -> List[Any]:
    return [
        condition
        for condition in conditions
        if _lower(condition.clinical_status) in ACTIVE_STATUS_VALUES or not condition.clinical_status
    ]


def _active_medications(medications: Iterable[Any]) -> List[Any]:
    return [
        medication
        for medication in medications
        if _lower(medication.status) in ACTIVE_MEDICATION_STATUSES or not medication.status
    ]


def _sort_by_date(records: Iterable[Any], attr_name: str) -> List[Any]:
    return sorted(records, key=lambda record: getattr(record, attr_name) or "", reverse=True)


def _format_value(value: Optional[str], unit: Optional[str]) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    if unit:
        return f"{value} {unit}"
    return str(value)


def _normalize_value(value: Optional[str], unit: Optional[str]) -> str:
    formatted = _format_value(value, unit)
    return _lower(formatted) or ""


def _lower(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def _is_after(left: Optional[str], right: Optional[str]) -> bool:
    left_date = _parse_datetime(left)
    right_date = _parse_datetime(right)
    if not left_date or not right_date:
        return False
    return left_date > right_date


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _matches_condition(condition, codes: Set[str], terms: Sequence[str]) -> bool:
    code = _lower(condition.condition_code)
    name = _lower(condition.condition_name) or ""
    return bool((code and code in codes) or any(term in name for term in terms))


def _has_observation(observations: Iterable[Any], codes: Set[str], terms: Sequence[str]) -> bool:
    for observation in observations:
        code = _lower(observation.observation_code)
        name = _lower(observation.observation_name) or ""
        if (code and code in codes) or any(term in name for term in terms):
            return True
    return False


def _source_record_count(patient) -> int:
    return (
        1
        + len(patient.conditions)
        + len(patient.observations)
        + len(patient.encounters)
        + len(patient.medication_requests)
        + len(patient.allergies)
    )
