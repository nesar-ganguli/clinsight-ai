from typing import Any, Dict, List, Optional

import httpx


SMART_HEALTH_IT_FHIR_BASE_URL = "https://r4.smarthealthit.org"
SMART_HEALTH_IT_SOURCE_MARKER = "smart-health-it-r4-sandbox"
SUPPORTED_PATIENT_RESOURCES = [
    "Condition",
    "Observation",
    "Encounter",
    "MedicationRequest",
    "AllergyIntolerance",
]


class SmartFhirClientError(Exception):
    pass


def search_smart_patients(
    search: Optional[str] = None,
    count: int = 10,
    base_url: str = SMART_HEALTH_IT_FHIR_BASE_URL,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"_count": count}
    if search:
        params["name"] = search

    bundle = _get_json(base_url, "Patient", params=params)
    patients = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Patient":
            continue
        patients.append(_patient_summary(resource))
    return patients


def fetch_smart_patient_bundle(
    patient_id: str,
    base_url: str = SMART_HEALTH_IT_FHIR_BASE_URL,
) -> Dict[str, Any]:
    patient = _get_json(base_url, f"Patient/{patient_id}")
    entries = [_entry(patient, base_url)]

    for resource_type in SUPPORTED_PATIENT_RESOURCES:
        resource_bundle = _get_json(base_url, resource_type, params={"patient": patient_id, "_count": 100})
        entries.extend(
            _entry(entry["resource"], base_url)
            for entry in resource_bundle.get("entry", [])
            if entry.get("resource", {}).get("resourceType") == resource_type
        )

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {
            "source": SMART_HEALTH_IT_SOURCE_MARKER,
            "tag": [
                {
                    "system": "https://clinsight.ai/source-type",
                    "code": "smart-health-it-r4-sandbox",
                    "display": "SMART Health IT R4 Sandbox",
                }
            ],
        },
        "entry": entries,
    }


def _get_json(base_url: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = httpx.get(url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise SmartFhirClientError(f"SMART FHIR request failed: {exc}") from exc
    except ValueError as exc:
        raise SmartFhirClientError("SMART FHIR server returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise SmartFhirClientError("SMART FHIR server returned an unexpected response")
    return payload


def _entry(resource: Dict[str, Any], base_url: str = SMART_HEALTH_IT_FHIR_BASE_URL) -> Dict[str, Any]:
    resource_type = resource.get("resourceType", "Resource")
    resource_id = resource.get("id", "unknown")
    return {
        "fullUrl": f"{base_url.rstrip('/')}/{resource_type}/{resource_id}",
        "resource": resource,
    }


def _patient_summary(patient: Dict[str, Any]) -> Dict[str, Optional[str]]:
    return {
        "id": patient.get("id"),
        "full_name": _human_name(patient),
        "gender": patient.get("gender"),
        "birth_date": patient.get("birthDate"),
    }


def _human_name(patient: Dict[str, Any]) -> Optional[str]:
    names = patient.get("name") or []
    if not names:
        return None

    name = names[0]
    parts = []
    parts.extend(name.get("given") or [])
    if name.get("family"):
        parts.append(name["family"])
    return " ".join(str(part) for part in parts if part) or name.get("text")
