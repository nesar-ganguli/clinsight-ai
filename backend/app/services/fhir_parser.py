from typing import Any, Dict, List, Optional

from app.core.temporal import parse_fhir_datetime


SUPPORTED_CHILD_RESOURCE_TYPES = {
    "Condition",
    "Observation",
    "Encounter",
    "MedicationRequest",
    "AllergyIntolerance",
}


class RecordValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def get_first_coding(resource: Dict[str, Any], field_name: str) -> Dict[str, Optional[str]]:
    """
    Extract the first coding code/display from a FHIR CodeableConcept field.
    """
    field = resource.get(field_name, {})
    if isinstance(field, list):
        field = field[0] if field else {}
    if not isinstance(field, dict):
        return {
            "code": None,
            "display": None
        }

    codings = field.get("coding", [])

    if codings and isinstance(codings, list):
        first = codings[0]
        return {
            "code": first.get("code"),
            "display": first.get("display")
        }

    return {
        "code": None,
        "display": field.get("text")
    }


def get_human_name(patient_resource: Dict[str, Any]) -> Optional[str]:
    """
    Extract a readable full name from Patient.name.
    """
    names = patient_resource.get("name", [])
    if not names:
        return None

    first_name_block = names[0]
    given = first_name_block.get("given", [])
    family = first_name_block.get("family")

    full_name_parts = []
    if given:
        full_name_parts.extend(given)
    if family:
        full_name_parts.append(family)

    return " ".join(full_name_parts) if full_name_parts else None


def extract_patient_reference(reference_obj: Dict[str, Any]) -> Optional[str]:
    """
    Extract patient id from references like 'Patient/123'.
    """
    if not reference_obj:
        return None

    ref = reference_obj.get("reference")
    if not ref or not isinstance(ref, str):
        return None

    if ref.startswith("Patient/"):
        return ref.split("/", 1)[1]

    if "/Patient/" in ref:
        return ref.rsplit("/Patient/", 1)[1]

    return ref


def parse_patient(resource: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Normalize a FHIR Patient resource.
    """
    return {
        "fhir_patient_id": resource.get("id"),
        "full_name": get_human_name(resource),
        "gender": resource.get("gender"),
        "birth_date": resource.get("birthDate")
    }


def parse_condition(resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a FHIR Condition resource.
    """
    code_data = get_first_coding(resource, "code")

    clinical_status = None
    clinical_status_field = resource.get("clinicalStatus", {})
    if clinical_status_field:
        coding = clinical_status_field.get("coding", [])
        if coding and isinstance(coding, list):
            clinical_status = coding[0].get("code")
        else:
            clinical_status = clinical_status_field.get("text")

    return {
        "fhir_condition_id": resource.get("id"),
        "patient_reference": extract_patient_reference(resource.get("subject", {})),
        "condition_code": code_data.get("code"),
        "condition_name": code_data.get("display"),
        "clinical_status": clinical_status,
        "onset_date": parse_fhir_datetime(resource.get("onsetDateTime"))
    }


def parse_observation(resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a FHIR Observation resource.
    Supports valueQuantity and valueString for now.
    """
    code_data = get_first_coding(resource, "code")

    value = None
    unit = None

    if "valueQuantity" in resource:
        value_quantity = resource.get("valueQuantity", {})
        value_num = value_quantity.get("value")
        unit = value_quantity.get("unit")
        value = str(value_num) if value_num is not None else None

    elif "valueString" in resource:
        value = resource.get("valueString")

    return {
        "fhir_observation_id": resource.get("id"),
        "patient_reference": extract_patient_reference(resource.get("subject", {})),
        "observation_code": code_data.get("code"),
        "observation_name": code_data.get("display"),
        "value": value,
        "unit": unit,
        "effective_date": parse_fhir_datetime(resource.get("effectiveDateTime"))
    }


def parse_encounter(resource: Dict[str, Any]) -> Dict[str, Any]:
    encounter_type = get_first_coding(resource, "type")
    encounter_class = resource.get("class", {})

    return {
        "fhir_encounter_id": resource.get("id"),
        "patient_reference": extract_patient_reference(resource.get("subject", {})),
        "status": resource.get("status"),
        "encounter_class": encounter_class.get("code") or encounter_class.get("display"),
        "encounter_type": encounter_type.get("display"),
        "period_start": parse_fhir_datetime(resource.get("period", {}).get("start")),
        "period_end": parse_fhir_datetime(resource.get("period", {}).get("end"))
    }


def parse_medication_request(resource: Dict[str, Any]) -> Dict[str, Any]:
    medication_data = get_first_coding(resource, "medicationCodeableConcept")

    return {
        "fhir_medication_request_id": resource.get("id"),
        "patient_reference": extract_patient_reference(resource.get("subject", {})),
        "status": resource.get("status"),
        "intent": resource.get("intent"),
        "medication_code": medication_data.get("code"),
        "medication_name": medication_data.get("display"),
        "authored_on": parse_fhir_datetime(resource.get("authoredOn"))
    }


def parse_allergy_intolerance(resource: Dict[str, Any]) -> Dict[str, Any]:
    allergy_data = get_first_coding(resource, "code")

    clinical_status = None
    clinical_status_field = resource.get("clinicalStatus", {})
    if clinical_status_field:
        clinical_status = get_first_coding(resource, "clinicalStatus").get("code")

    verification_status = None
    verification_status_field = resource.get("verificationStatus", {})
    if verification_status_field:
        verification_status = get_first_coding(resource, "verificationStatus").get("code")

    return {
        "fhir_allergy_id": resource.get("id"),
        "patient_reference": extract_patient_reference(resource.get("patient", {})),
        "clinical_status": clinical_status,
        "verification_status": verification_status,
        "allergy_code": allergy_data.get("code"),
        "allergy_name": allergy_data.get("display"),
        "criticality": resource.get("criticality"),
        "recorded_date": parse_fhir_datetime(resource.get("recordedDate"))
    }


def parse_fhir_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a FHIR Bundle and extract supported clinical resources.
    Assumes one main patient per bundle for MVP.
    """
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        raise ValueError("FHIR Bundle entry must be a list")

    patient_data = None
    conditions: List[Dict[str, Any]] = []
    observations: List[Dict[str, Any]] = []
    encounters: List[Dict[str, Any]] = []
    medication_requests: List[Dict[str, Any]] = []
    allergies: List[Dict[str, Any]] = []
    resource_counts: Dict[str, int] = {}
    quarantined_resources: List[Dict[str, Any]] = []
    unsupported_count = 0
    typed_resources: List[Dict[str, Any]] = []

    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("resource"), dict):
            quarantined_resources.append(
                _quarantine_item(
                    resource_type="Unknown",
                    source_record_id=None,
                    error_code="malformed_bundle_entry",
                    error_message="Bundle entry must contain a JSON resource object.",
                    raw_payload=entry,
                )
            )
            continue

        resource = entry["resource"]
        resource_type = resource.get("resourceType")

        if not isinstance(resource_type, str) or not resource_type.strip():
            quarantined_resources.append(
                _quarantine_item(
                    resource_type="Unknown",
                    source_record_id=_source_record_id(resource),
                    error_code="missing_resource_type",
                    error_message="Resource is missing a valid resourceType.",
                    raw_payload=resource,
                )
            )
            continue

        resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1
        typed_resources.append(resource)

    for resource in typed_resources:
        if resource["resourceType"] != "Patient":
            continue

        if patient_data is not None:
            quarantined_resources.append(
                _quarantine_item(
                    resource_type="Patient",
                    source_record_id=_source_record_id(resource),
                    error_code="additional_patient_not_supported",
                    error_message="Only one Patient resource can be ingested per Bundle.",
                    raw_payload=resource,
                )
            )
            continue

        try:
            patient_data = _parse_patient_resource(resource)
        except RecordValidationError as exc:
            quarantined_resources.append(
                _quarantine_item(
                    resource_type="Patient",
                    source_record_id=_source_record_id(resource),
                    error_code=exc.code,
                    error_message=exc.message,
                    raw_payload=resource,
                )
            )
            continue
        except (AttributeError, TypeError, ValueError):
            quarantined_resources.append(
                _quarantine_item(
                    resource_type="Patient",
                    source_record_id=_source_record_id(resource),
                    error_code="malformed_resource",
                    error_message="Patient structure cannot be transformed by the supported parser.",
                    raw_payload=resource,
                )
            )
            continue

    if patient_data is None:
        raise ValueError("No usable Patient resource found in bundle")

    patient_id = patient_data["fhir_patient_id"]
    parsed_collections = {
        "Condition": conditions,
        "Observation": observations,
        "Encounter": encounters,
        "MedicationRequest": medication_requests,
        "AllergyIntolerance": allergies,
    }

    for resource in typed_resources:
        resource_type = resource["resourceType"]
        if resource_type == "Patient":
            continue

        if resource_type not in SUPPORTED_CHILD_RESOURCE_TYPES:
            unsupported_count += 1
            continue

        try:
            parsed_resource = _parse_child_resource(resource, patient_id)
        except RecordValidationError as exc:
            quarantined_resources.append(
                _quarantine_item(
                    resource_type=resource_type,
                    source_record_id=_source_record_id(resource),
                    error_code=exc.code,
                    error_message=exc.message,
                    raw_payload=resource,
                )
            )
            continue
        except (AttributeError, TypeError, ValueError):
            quarantined_resources.append(
                _quarantine_item(
                    resource_type=resource_type,
                    source_record_id=_source_record_id(resource),
                    error_code="malformed_resource",
                    error_message="Resource structure cannot be transformed by the supported parser.",
                    raw_payload=resource,
                )
            )
            continue

        parsed_collections[resource_type].append(parsed_resource)

    return {
        "patient": patient_data,
        "conditions": conditions,
        "observations": observations,
        "encounters": encounters,
        "medication_requests": medication_requests,
        "allergies": allergies,
        "resource_counts": resource_counts,
        "raw_bundle_type": bundle.get("type"),
        "record_count": len(entries),
        "unsupported_count": unsupported_count,
        "quarantined_resources": quarantined_resources,
    }


def _parse_patient_resource(resource: Dict[str, Any]) -> Dict[str, Any]:
    parsed = parse_patient(resource)
    if not _nonempty_string(parsed.get("fhir_patient_id")):
        raise RecordValidationError(
            "missing_patient_id",
            "Patient resource is missing a usable id.",
        )
    return parsed


def _parse_child_resource(resource: Dict[str, Any], patient_id: str) -> Dict[str, Any]:
    resource_type = resource["resourceType"]
    if not _nonempty_string(resource.get("id")):
        raise RecordValidationError(
            "missing_resource_id",
            f"{resource_type} resource is missing a usable id.",
        )

    parser = {
        "Condition": parse_condition,
        "Observation": parse_observation,
        "Encounter": parse_encounter,
        "MedicationRequest": parse_medication_request,
        "AllergyIntolerance": parse_allergy_intolerance,
    }[resource_type]
    parsed = parser(resource)
    _validate_patient_reference(resource_type, parsed.get("patient_reference"), patient_id)

    if resource_type == "Condition":
        _require_code(resource_type, parsed.get("condition_code"), parsed.get("condition_name"))
        _validate_optional_datetime(resource, "onsetDateTime", parsed.get("onset_date"))
    elif resource_type == "Observation":
        _require_code(resource_type, parsed.get("observation_code"), parsed.get("observation_name"))
        _validate_observation_value(resource, parsed.get("value"))
        _validate_optional_datetime(resource, "effectiveDateTime", parsed.get("effective_date"))
    elif resource_type == "Encounter":
        _require_field(resource_type, "status", parsed.get("status"))
        period = resource.get("period", {})
        if period is not None and not isinstance(period, dict):
            raise RecordValidationError(
                "malformed_period",
                "Encounter period must be a JSON object when supplied.",
            )
        _validate_optional_datetime(period or {}, "start", parsed.get("period_start"))
        _validate_optional_datetime(period or {}, "end", parsed.get("period_end"))
    elif resource_type == "MedicationRequest":
        _require_field(resource_type, "status", parsed.get("status"))
        _require_field(resource_type, "intent", parsed.get("intent"))
        _require_code(resource_type, parsed.get("medication_code"), parsed.get("medication_name"))
        _validate_optional_datetime(resource, "authoredOn", parsed.get("authored_on"))
    elif resource_type == "AllergyIntolerance":
        _require_code(resource_type, parsed.get("allergy_code"), parsed.get("allergy_name"))
        _validate_optional_datetime(resource, "recordedDate", parsed.get("recorded_date"))

    return parsed


def _validate_patient_reference(
    resource_type: str,
    patient_reference: Optional[str],
    patient_id: str,
) -> None:
    if not _nonempty_string(patient_reference):
        raise RecordValidationError(
            "missing_patient_reference",
            f"{resource_type} resource is missing a patient reference.",
        )
    if patient_reference != patient_id:
        raise RecordValidationError(
            "patient_reference_mismatch",
            f"{resource_type} resource references a different Patient.",
        )


def _require_code(resource_type: str, code: Any, display: Any) -> None:
    if not _nonempty_string(code) and not _nonempty_string(display):
        raise RecordValidationError(
            "missing_required_code",
            f"{resource_type} resource is missing a transformable code or display.",
        )


def _require_field(resource_type: str, field_name: str, value: Any) -> None:
    if not _nonempty_string(value):
        raise RecordValidationError(
            f"missing_{field_name}",
            f"{resource_type} resource is missing required field {field_name}.",
        )


def _validate_observation_value(resource: Dict[str, Any], parsed_value: Any) -> None:
    if "valueQuantity" in resource:
        quantity = resource.get("valueQuantity")
        if not isinstance(quantity, dict) or quantity.get("value") is None:
            raise RecordValidationError(
                "invalid_observation_value",
                "Observation valueQuantity must contain a value.",
            )
    elif "valueString" in resource:
        if not _nonempty_string(parsed_value):
            raise RecordValidationError(
                "invalid_observation_value",
                "Observation valueString must contain a value.",
            )
    else:
        raise RecordValidationError(
            "unsupported_observation_value",
            "Observation value representation is not supported.",
        )


def _validate_optional_datetime(
    container: Dict[str, Any],
    field_name: str,
    parsed_value: Any,
) -> None:
    if field_name in container and container.get(field_name) is not None and parsed_value is None:
        raise RecordValidationError(
            "invalid_datetime",
            f"Field {field_name} is not a supported FHIR date or dateTime.",
        )


def _source_record_id(resource: Dict[str, Any]) -> Optional[str]:
    resource_id = resource.get("id")
    return resource_id if isinstance(resource_id, str) else None


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _quarantine_item(
    resource_type: str,
    source_record_id: Optional[str],
    error_code: str,
    error_message: str,
    raw_payload: Any,
) -> Dict[str, Any]:
    return {
        "resource_type": resource_type,
        "source_record_id": source_record_id,
        "error_code": error_code,
        "error_message": error_message,
        "raw_payload": raw_payload,
    }
