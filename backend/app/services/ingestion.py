import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type

from sqlalchemy.orm import Session

from app.models.allergy_intolerance import AllergyIntolerance
from app.models.condition import Condition
from app.models.curated_record_source import CuratedRecordSource
from app.models.encounter import Encounter
from app.models.ingestion_batch import IngestionBatch
from app.models.medication_request import MedicationRequest
from app.models.observation import Observation
from app.models.patient import Patient
from app.models.patient_source_identifier import PatientSourceIdentifier
from app.models.quarantine_record import QuarantineRecord
from app.models.source_system import SourceSystem
from app.services.fhir_parser import parse_fhir_bundle


FHIR_UPLOAD_SOURCE_NAME = "ClinSight FHIR Upload"
GENERATED_FHIR_SOURCE_NAME = "ClinSight Generated FHIR Bundle"
SMART_HEALTH_IT_SOURCE_NAME = "SMART Health IT R4 Sandbox"
FHIR_UPLOAD_TRANSFORM_VERSION = "fhir-upload-v1"
GENERATED_FHIR_SOURCE_MARKER = "clinsight-generated-fhir-bundle"
SMART_HEALTH_IT_SOURCE_MARKER = "smart-health-it-r4-sandbox"
SAFE_INGESTION_ERROR_MESSAGES = {
    "No Patient resource found in bundle",
    "No usable Patient resource found in bundle",
    "FHIR Bundle entry must be a list",
    "Source patient identifier is already mapped to another canonical patient",
}


def ingest_fhir_bundle(
    bundle: Dict[str, Any],
    db: Session,
    filename: Optional[str] = None,
    content_hash: Optional[str] = None,
) -> Dict[str, Any]:
    source_system = _get_or_create_fhir_source(db, bundle)
    started_at = datetime.now(timezone.utc)
    ingestion_batch = IngestionBatch(
        source_system_id=source_system.id,
        ingestion_type=source_system.system_type,
        filename=filename,
        content_hash=content_hash or _hash_bundle(bundle),
        status="processing",
        record_count=_count_bundle_resources(bundle),
        accepted_count=0,
        rejected_count=0,
        started_at=started_at,
    )
    db.add(ingestion_batch)
    db.flush()
    ingestion_batch_id = ingestion_batch.id
    source_system_id = source_system.id
    db.commit()

    try:
        persisted_batch = db.get(IngestionBatch, ingestion_batch_id)
        persisted_source = db.get(SourceSystem, source_system_id)
        return _ingest_fhir_bundle_clinical(
            bundle,
            db,
            source_system=persisted_source,
            ingestion_batch=persisted_batch,
        )
    except Exception as exc:
        db.rollback()
        _mark_ingestion_batch_failed(db, ingestion_batch_id, exc)
        raise


def _ingest_fhir_bundle_clinical(
    bundle: Dict[str, Any],
    db: Session,
    source_system: SourceSystem,
    ingestion_batch: IngestionBatch,
) -> Dict[str, Any]:
    parsed_data = parse_fhir_bundle(bundle)
    patient_payload = parsed_data.get("patient")

    if not patient_payload:
        raise ValueError("No usable Patient resource found in bundle")

    transformed_at = datetime.now(timezone.utc)

    for rejected_resource in parsed_data.get("quarantined_resources", []):
        db.add(
            QuarantineRecord(
                ingestion_batch_id=ingestion_batch.id,
                source_system_id=source_system.id,
                resource_type=rejected_resource["resource_type"],
                source_record_id=rejected_resource.get("source_record_id"),
                error_code=rejected_resource["error_code"],
                error_message=rejected_resource["error_message"],
                raw_payload=rejected_resource["raw_payload"],
            )
        )

    import_mode = "created"
    fhir_patient_id = patient_payload.get("fhir_patient_id")
    patient = _resolve_patient_by_source_identifier(
        db,
        source_system.id,
        fhir_patient_id,
    )

    if patient:
        import_mode = "updated"
        patient.full_name = patient_payload.get("full_name")
        patient.gender = patient_payload.get("gender")
        patient.birth_date = patient_payload.get("birth_date")
        _apply_source_metadata(
            patient,
            source_system,
            ingestion_batch.id,
            fhir_patient_id,
            transformed_at,
        )

    else:
        patient = Patient(
            fhir_patient_id=fhir_patient_id,
            full_name=patient_payload.get("full_name"),
            gender=patient_payload.get("gender"),
            birth_date=patient_payload.get("birth_date"),
        )
        _apply_source_metadata(
            patient,
            source_system,
            ingestion_batch.id,
            fhir_patient_id,
            transformed_at,
        )
        db.add(patient)
        db.flush()

    _upsert_curated_source(
        db,
        "patients",
        patient.id,
        source_system.id,
        ingestion_batch.id,
        raw_record_id=fhir_patient_id,
    )
    _upsert_patient_source_identifier(
        db,
        patient,
        source_system.id,
        ingestion_batch.id,
        fhir_patient_id,
    )

    for cond in parsed_data.get("conditions", []):
        _upsert_clinical_record(
            db,
            model=Condition,
            patient=patient,
            source_system=source_system,
            ingestion_batch=ingestion_batch,
            transformed_at=transformed_at,
            curated_table_name="conditions",
            fhir_id_attribute="fhir_condition_id",
            fhir_resource_id=cond.get("fhir_condition_id"),
            values={
                "condition_code": cond.get("condition_code"),
                "condition_name": cond.get("condition_name"),
                "clinical_status": cond.get("clinical_status"),
                "onset_date": cond.get("onset_date"),
            },
        )

    for obs in parsed_data.get("observations", []):
        _upsert_clinical_record(
            db,
            model=Observation,
            patient=patient,
            source_system=source_system,
            ingestion_batch=ingestion_batch,
            transformed_at=transformed_at,
            curated_table_name="observations",
            fhir_id_attribute="fhir_observation_id",
            fhir_resource_id=obs.get("fhir_observation_id"),
            values={
                "observation_code": obs.get("observation_code"),
                "observation_name": obs.get("observation_name"),
                "value": obs.get("value"),
                "unit": obs.get("unit"),
                "effective_date": obs.get("effective_date"),
            },
        )

    for encounter in parsed_data.get("encounters", []):
        _upsert_clinical_record(
            db,
            model=Encounter,
            patient=patient,
            source_system=source_system,
            ingestion_batch=ingestion_batch,
            transformed_at=transformed_at,
            curated_table_name="encounters",
            fhir_id_attribute="fhir_encounter_id",
            fhir_resource_id=encounter.get("fhir_encounter_id"),
            values={
                "status": encounter.get("status"),
                "encounter_class": encounter.get("encounter_class"),
                "encounter_type": encounter.get("encounter_type"),
                "period_start": encounter.get("period_start"),
                "period_end": encounter.get("period_end"),
            },
        )

    for medication in parsed_data.get("medication_requests", []):
        _upsert_clinical_record(
            db,
            model=MedicationRequest,
            patient=patient,
            source_system=source_system,
            ingestion_batch=ingestion_batch,
            transformed_at=transformed_at,
            curated_table_name="medication_requests",
            fhir_id_attribute="fhir_medication_request_id",
            fhir_resource_id=medication.get("fhir_medication_request_id"),
            values={
                "status": medication.get("status"),
                "intent": medication.get("intent"),
                "medication_code": medication.get("medication_code"),
                "medication_name": medication.get("medication_name"),
                "authored_on": medication.get("authored_on"),
            },
        )

    for allergy in parsed_data.get("allergies", []):
        _upsert_clinical_record(
            db,
            model=AllergyIntolerance,
            patient=patient,
            source_system=source_system,
            ingestion_batch=ingestion_batch,
            transformed_at=transformed_at,
            curated_table_name="allergy_intolerances",
            fhir_id_attribute="fhir_allergy_id",
            fhir_resource_id=allergy.get("fhir_allergy_id"),
            values={
                "clinical_status": allergy.get("clinical_status"),
                "verification_status": allergy.get("verification_status"),
                "allergy_code": allergy.get("allergy_code"),
                "allergy_name": allergy.get("allergy_name"),
                "criticality": allergy.get("criticality"),
                "recorded_date": allergy.get("recorded_date"),
            },
        )

    resource_counts = parsed_data.get("resource_counts", {})
    record_count = parsed_data.get("record_count", sum(resource_counts.values()))
    accepted_count = _accepted_resource_count(parsed_data)
    rejected_count = len(parsed_data.get("quarantined_resources", []))
    unsupported_count = parsed_data.get("unsupported_count", 0)
    ingestion_batch.status = "success"
    ingestion_batch.record_count = record_count
    ingestion_batch.accepted_count = accepted_count
    ingestion_batch.rejected_count = rejected_count
    ingestion_batch.error_message = None
    ingestion_batch.completed_at = datetime.now(timezone.utc)

    result = {
        "patient_id": patient.id,
        "import_mode": import_mode,
        "resource_counts": resource_counts,
        "ingestion_summary": {
            "accepted": accepted_count,
            "rejected": rejected_count,
            "unsupported": unsupported_count,
        },
    }
    db.commit()
    return result


def _count_bundle_resources(bundle: Dict[str, Any]) -> int:
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        return 0

    return len(entries)


def _accepted_resource_count(parsed_data: Dict[str, Any]) -> int:
    accepted_count = 1 if parsed_data.get("patient") else 0
    for key in (
        "conditions",
        "observations",
        "encounters",
        "medication_requests",
        "allergies",
    ):
        accepted_count += len(parsed_data.get(key, []))
    return accepted_count


def _mark_ingestion_batch_failed(db: Session, ingestion_batch_id: int, exc: Exception) -> None:
    ingestion_batch = db.get(IngestionBatch, ingestion_batch_id)
    if ingestion_batch is None:
        raise RuntimeError(f"Persisted ingestion batch {ingestion_batch_id} was not found") from exc

    ingestion_batch.status = "failed"
    ingestion_batch.accepted_count = 0
    ingestion_batch.rejected_count = ingestion_batch.record_count
    ingestion_batch.error_message = _sanitize_ingestion_error(exc)
    ingestion_batch.completed_at = datetime.now(timezone.utc)
    db.commit()


def _sanitize_ingestion_error(exc: Exception) -> str:
    message = " ".join(str(exc).split())
    if isinstance(exc, ValueError) and message in SAFE_INGESTION_ERROR_MESSAGES:
        return message
    return f"{type(exc).__name__}: FHIR bundle ingestion failed"


def _get_or_create_fhir_source(db: Session, bundle: Dict[str, Any]) -> SourceSystem:
    if _is_generated_fhir_bundle(bundle):
        return _get_or_create_source_system(
            db,
            name=GENERATED_FHIR_SOURCE_NAME,
            system_type="generated_fhir_bundle",
            facility_name="ClinSight synthetic FHIR generator",
            external_system_id=GENERATED_FHIR_SOURCE_MARKER,
        )
    if _is_smart_health_it_bundle(bundle):
        return _get_or_create_source_system(
            db,
            name=SMART_HEALTH_IT_SOURCE_NAME,
            system_type="external_fhir_api",
            facility_name="SMART Health IT public sandbox",
            external_system_id=SMART_HEALTH_IT_SOURCE_MARKER,
        )

    return _get_or_create_source_system(
        db,
        name=FHIR_UPLOAD_SOURCE_NAME,
        system_type="fhir_upload",
        facility_name="ClinSight demo upload",
        external_system_id="clinsight-fhir-upload",
    )


def _get_or_create_source_system(
    db: Session,
    name: str,
    system_type: str,
    facility_name: str,
    external_system_id: str,
) -> SourceSystem:
    source_system = (
        db.query(SourceSystem)
        .filter(SourceSystem.name == name)
        .first()
    )
    if source_system:
        return source_system

    source_system = SourceSystem(
        name=name,
        system_type=system_type,
        facility_name=facility_name,
        external_system_id=external_system_id,
        is_active=True,
    )
    db.add(source_system)
    db.flush()
    return source_system


def _is_generated_fhir_bundle(bundle: Dict[str, Any]) -> bool:
    meta = bundle.get("meta", {})
    if meta.get("source") == GENERATED_FHIR_SOURCE_MARKER:
        return True

    tags = meta.get("tag", [])
    return any(tag.get("code") == "generated-fhir-bundle" for tag in tags if isinstance(tag, dict))


def _is_smart_health_it_bundle(bundle: Dict[str, Any]) -> bool:
    meta = bundle.get("meta", {})
    if meta.get("source") == SMART_HEALTH_IT_SOURCE_MARKER:
        return True

    tags = meta.get("tag", [])
    return any(tag.get("code") == "smart-health-it-r4-sandbox" for tag in tags if isinstance(tag, dict))


def _apply_source_metadata(
    record: Any,
    source_system: SourceSystem,
    ingestion_batch_id: int,
    source_record_id: Optional[str],
    transformed_at: datetime,
) -> None:
    record.source_type = source_system.system_type
    record.source_system = source_system.name
    record.source_record_id = source_record_id
    record.ingestion_batch_id = str(ingestion_batch_id)
    record.transformed_at = transformed_at


def _hash_bundle(bundle: Dict[str, Any]) -> str:
    canonical_bundle = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_bundle.encode("utf-8")).hexdigest()


def _upsert_patient_source_identifier(
    db: Session,
    patient: Patient,
    source_system_id: int,
    ingestion_batch_id: int,
    source_patient_id: Optional[str],
) -> None:
    if not source_patient_id:
        return

    identifier = (
        db.query(PatientSourceIdentifier)
        .filter(
            PatientSourceIdentifier.source_system_id == source_system_id,
            PatientSourceIdentifier.identifier_value == source_patient_id,
        )
        .first()
    )
    if identifier:
        if identifier.patient_id != patient.id:
            raise ValueError("Source patient identifier is already mapped to another canonical patient")
        identifier.last_seen_batch_id = ingestion_batch_id
    else:
        db.add(
            PatientSourceIdentifier(
                patient_id=patient.id,
                source_system_id=source_system_id,
                identifier_type="fhir_patient_id",
                identifier_value=source_patient_id,
                assigning_authority="FHIR Bundle",
                last_seen_batch_id=ingestion_batch_id,
            )
        )


def _resolve_patient_by_source_identifier(
    db: Session,
    source_system_id: int,
    source_patient_id: Optional[str],
) -> Optional[Patient]:
    if not source_patient_id:
        return None

    identifier = (
        db.query(PatientSourceIdentifier)
        .filter(
            PatientSourceIdentifier.source_system_id == source_system_id,
            PatientSourceIdentifier.identifier_value == source_patient_id,
        )
        .first()
    )
    if identifier is None:
        return None

    return db.query(Patient).filter(Patient.id == identifier.patient_id).first()


def _upsert_clinical_record(
    db: Session,
    model: Type[Any],
    patient: Patient,
    source_system: SourceSystem,
    ingestion_batch: IngestionBatch,
    transformed_at: datetime,
    curated_table_name: str,
    fhir_id_attribute: str,
    fhir_resource_id: Optional[str],
    values: Dict[str, Any],
) -> Any:
    record = None
    if fhir_resource_id:
        record = (
            db.query(model)
            .filter(
                model.patient_id == patient.id,
                model.source_system == source_system.name,
                getattr(model, fhir_id_attribute) == fhir_resource_id,
            )
            .first()
        )

    if record is None:
        record = model(
            patient_id=patient.id,
            **{fhir_id_attribute: fhir_resource_id},
        )
        db.add(record)

    for attribute, value in values.items():
        setattr(record, attribute, value)

    _apply_source_metadata(
        record,
        source_system,
        ingestion_batch.id,
        fhir_resource_id,
        transformed_at,
    )
    db.flush()
    _upsert_curated_source(
        db,
        curated_table_name,
        record.id,
        source_system.id,
        ingestion_batch.id,
        raw_record_id=fhir_resource_id,
    )
    return record


def _upsert_curated_source(
    db: Session,
    curated_table_name: str,
    curated_record_id: int,
    source_system_id: int,
    ingestion_batch_id: int,
    raw_record_id: Optional[str] = None,
) -> None:
    curated_source = (
        db.query(CuratedRecordSource)
        .filter(
            CuratedRecordSource.curated_table_name == curated_table_name,
            CuratedRecordSource.curated_record_id == curated_record_id,
            CuratedRecordSource.source_system_id == source_system_id,
        )
        .first()
    )
    if curated_source is None:
        curated_source = CuratedRecordSource(
            curated_table_name=curated_table_name,
            curated_record_id=curated_record_id,
            source_system_id=source_system_id,
        )
        db.add(curated_source)

    curated_source.ingestion_batch_id = ingestion_batch_id
    curated_source.raw_table_name = "fhir_bundle"
    curated_source.raw_record_id = raw_record_id
    curated_source.transform_version = FHIR_UPLOAD_TRANSFORM_VERSION
