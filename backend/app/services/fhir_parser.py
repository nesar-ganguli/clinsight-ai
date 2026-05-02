from typing import Any, Dict, List, Optional


def get_first_coding(resource: Dict[str, Any], field_name: str) -> Dict[str, Optional[str]]:
    """
    Extract the first coding code/display from a FHIR CodeableConcept field.
    """
    field = resource.get(field_name, {})
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


def parse_condition(resource: Dict[str, Any]) -> Dict[str, Optional[str]]:
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
        "onset_date": resource.get("onsetDateTime")
    }


def parse_observation(resource: Dict[str, Any]) -> Dict[str, Optional[str]]:
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
        "effective_date": resource.get("effectiveDateTime")
    }


def parse_encounter(resource: Dict[str, Any]) -> Dict[str, Optional[str]]:
    encounter_type = get_first_coding(resource, "type")
    encounter_class = resource.get("class", {})

    return {
        "fhir_encounter_id": resource.get("id"),
        "patient_reference": extract_patient_reference(resource.get("subject", {})),
        "status": resource.get("status"),
        "encounter_class": encounter_class.get("code") or encounter_class.get("display"),
        "encounter_type": encounter_type.get("display"),
        "period_start": resource.get("period", {}).get("start"),
        "period_end": resource.get("period", {}).get("end")
    }


def parse_medication_request(resource: Dict[str, Any]) -> Dict[str, Optional[str]]:
    medication_data = get_first_coding(resource, "medicationCodeableConcept")

    return {
        "fhir_medication_request_id": resource.get("id"),
        "patient_reference": extract_patient_reference(resource.get("subject", {})),
        "status": resource.get("status"),
        "intent": resource.get("intent"),
        "medication_code": medication_data.get("code"),
        "medication_name": medication_data.get("display"),
        "authored_on": resource.get("authoredOn")
    }


def parse_allergy_intolerance(resource: Dict[str, Any]) -> Dict[str, Optional[str]]:
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
        "recorded_date": resource.get("recordedDate")
    }


def parse_fhir_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a FHIR Bundle and extract supported clinical resources.
    Assumes one main patient per bundle for MVP.
    """
    entries = bundle.get("entry", [])

    patient_data = None
    conditions: List[Dict[str, Any]] = []
    observations: List[Dict[str, Any]] = []
    encounters: List[Dict[str, Any]] = []
    medication_requests: List[Dict[str, Any]] = []
    allergies: List[Dict[str, Any]] = []
    resource_counts: Dict[str, int] = {}

    for entry in entries:
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")

        if not resource_type:
            continue

        resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1

        if resource_type == "Patient" and patient_data is None:
            patient_data = parse_patient(resource)

        elif resource_type == "Condition":
            conditions.append(parse_condition(resource))

        elif resource_type == "Observation":
            observations.append(parse_observation(resource))

        elif resource_type == "Encounter":
            encounters.append(parse_encounter(resource))

        elif resource_type == "MedicationRequest":
            medication_requests.append(parse_medication_request(resource))

        elif resource_type == "AllergyIntolerance":
            allergies.append(parse_allergy_intolerance(resource))

    return {
        "patient": patient_data,
        "conditions": conditions,
        "observations": observations,
        "encounters": encounters,
        "medication_requests": medication_requests,
        "allergies": allergies,
        "resource_counts": resource_counts,
        "raw_bundle_type": bundle.get("type")
    }
