import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
from app.models.source_system import SourceSystem
from app.services.fhir_parser import parse_fhir_bundle


FHIR_UPLOAD_SOURCE_NAME = "ClinSight FHIR Upload"
GENERATED_FHIR_SOURCE_NAME = "ClinSight Generated FHIR Bundle"
FHIR_UPLOAD_TRANSFORM_VERSION = "fhir-upload-v1"
GENERATED_FHIR_SOURCE_MARKER = "clinsight-generated-fhir-bundle"


def ingest_fhir_bundle(
    bundle: Dict[str, Any],
    db: Session,
    filename: Optional[str] = None,
    content_hash: Optional[str] = None,
) -> Dict[str, Any]:
    parsed_data = parse_fhir_bundle(bundle)
    patient_payload = parsed_data.get("patient")

    if not patient_payload:
        raise ValueError("No Patient resource found in bundle")

    source_system = _get_or_create_fhir_source(db, bundle)
    transformed_at = datetime.now(timezone.utc)
    ingestion_batch = IngestionBatch(
        source_system_id=source_system.id,
        ingestion_type=source_system.system_type,
        filename=filename,
        content_hash=content_hash or _hash_bundle(bundle),
        status="processed",
        record_count=sum(parsed_data.get("resource_counts", {}).values()),
        processed_at=transformed_at
    )
    db.add(ingestion_batch)
    db.flush()

    patient = None
    import_mode = "created"
    fhir_patient_id = patient_payload.get("fhir_patient_id")

    if fhir_patient_id:
        patient = (
            db.query(Patient)
            .filter(Patient.fhir_patient_id == fhir_patient_id)
            .first()
        )

    if patient:
        import_mode = "updated"
        _delete_existing_curated_source_rows(db, patient, source_system.id)

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

        db.query(AllergyIntolerance).filter(AllergyIntolerance.patient_id == patient.id).delete()
        db.query(Condition).filter(Condition.patient_id == patient.id).delete()
        db.query(Encounter).filter(Encounter.patient_id == patient.id).delete()
        db.query(MedicationRequest).filter(MedicationRequest.patient_id == patient.id).delete()
        db.query(Observation).filter(Observation.patient_id == patient.id).delete()
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

    _add_curated_source(
        db,
        "patients",
        patient.id,
        source_system.id,
        ingestion_batch.id,
        raw_record_id=fhir_patient_id,
    )
    _upsert_patient_source_identifier(db, patient, source_system.id, ingestion_batch.id)

    for cond in parsed_data.get("conditions", []):
        condition = Condition(
            patient_id=patient.id,
            fhir_condition_id=cond.get("fhir_condition_id"),
            condition_code=cond.get("condition_code"),
            condition_name=cond.get("condition_name"),
            clinical_status=cond.get("clinical_status"),
            onset_date=cond.get("onset_date")
        )
        _apply_source_metadata(
            condition,
            source_system,
            ingestion_batch.id,
            cond.get("fhir_condition_id"),
            transformed_at,
        )
        db.add(condition)
        db.flush()
        _add_curated_source(
            db,
            "conditions",
            condition.id,
            source_system.id,
            ingestion_batch.id,
            raw_record_id=cond.get("fhir_condition_id"),
        )

    for obs in parsed_data.get("observations", []):
        observation = Observation(
            patient_id=patient.id,
            fhir_observation_id=obs.get("fhir_observation_id"),
            observation_code=obs.get("observation_code"),
            observation_name=obs.get("observation_name"),
            value=obs.get("value"),
            unit=obs.get("unit"),
            effective_date=obs.get("effective_date")
        )
        _apply_source_metadata(
            observation,
            source_system,
            ingestion_batch.id,
            obs.get("fhir_observation_id"),
            transformed_at,
        )
        db.add(observation)
        db.flush()
        _add_curated_source(
            db,
            "observations",
            observation.id,
            source_system.id,
            ingestion_batch.id,
            raw_record_id=obs.get("fhir_observation_id"),
        )

    for encounter in parsed_data.get("encounters", []):
        encounter_record = Encounter(
            patient_id=patient.id,
            fhir_encounter_id=encounter.get("fhir_encounter_id"),
            status=encounter.get("status"),
            encounter_class=encounter.get("encounter_class"),
            encounter_type=encounter.get("encounter_type"),
            period_start=encounter.get("period_start"),
            period_end=encounter.get("period_end")
        )
        _apply_source_metadata(
            encounter_record,
            source_system,
            ingestion_batch.id,
            encounter.get("fhir_encounter_id"),
            transformed_at,
        )
        db.add(encounter_record)
        db.flush()
        _add_curated_source(
            db,
            "encounters",
            encounter_record.id,
            source_system.id,
            ingestion_batch.id,
            raw_record_id=encounter.get("fhir_encounter_id"),
        )

    for medication in parsed_data.get("medication_requests", []):
        medication_request = MedicationRequest(
            patient_id=patient.id,
            fhir_medication_request_id=medication.get("fhir_medication_request_id"),
            status=medication.get("status"),
            intent=medication.get("intent"),
            medication_code=medication.get("medication_code"),
            medication_name=medication.get("medication_name"),
            authored_on=medication.get("authored_on")
        )
        _apply_source_metadata(
            medication_request,
            source_system,
            ingestion_batch.id,
            medication.get("fhir_medication_request_id"),
            transformed_at,
        )
        db.add(medication_request)
        db.flush()
        _add_curated_source(
            db,
            "medication_requests",
            medication_request.id,
            source_system.id,
            ingestion_batch.id,
            raw_record_id=medication.get("fhir_medication_request_id"),
        )

    for allergy in parsed_data.get("allergies", []):
        allergy_intolerance = AllergyIntolerance(
            patient_id=patient.id,
            fhir_allergy_id=allergy.get("fhir_allergy_id"),
            clinical_status=allergy.get("clinical_status"),
            verification_status=allergy.get("verification_status"),
            allergy_code=allergy.get("allergy_code"),
            allergy_name=allergy.get("allergy_name"),
            criticality=allergy.get("criticality"),
            recorded_date=allergy.get("recorded_date")
        )
        _apply_source_metadata(
            allergy_intolerance,
            source_system,
            ingestion_batch.id,
            allergy.get("fhir_allergy_id"),
            transformed_at,
        )
        db.add(allergy_intolerance)
        db.flush()
        _add_curated_source(
            db,
            "allergy_intolerances",
            allergy_intolerance.id,
            source_system.id,
            ingestion_batch.id,
            raw_record_id=allergy.get("fhir_allergy_id"),
        )

    db.commit()
    db.refresh(patient)

    return {
        "patient_id": patient.id,
        "import_mode": import_mode,
        "resource_counts": parsed_data.get("resource_counts", {}),
    }


def _get_or_create_fhir_source(db: Session, bundle: Dict[str, Any]) -> SourceSystem:
    if _is_generated_fhir_bundle(bundle):
        return _get_or_create_source_system(
            db,
            name=GENERATED_FHIR_SOURCE_NAME,
            system_type="generated_fhir_bundle",
            facility_name="ClinSight synthetic FHIR generator",
            external_system_id=GENERATED_FHIR_SOURCE_MARKER,
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
) -> None:
    if not patient.fhir_patient_id:
        return

    identifier = (
        db.query(PatientSourceIdentifier)
        .filter(
            PatientSourceIdentifier.source_system_id == source_system_id,
            PatientSourceIdentifier.identifier_type == "fhir_patient_id",
            PatientSourceIdentifier.identifier_value == patient.fhir_patient_id,
        )
        .first()
    )
    if identifier:
        identifier.patient_id = patient.id
        identifier.last_seen_batch_id = ingestion_batch_id
    else:
        db.add(
            PatientSourceIdentifier(
                patient_id=patient.id,
                source_system_id=source_system_id,
                identifier_type="fhir_patient_id",
                identifier_value=patient.fhir_patient_id,
                assigning_authority="FHIR Bundle",
                last_seen_batch_id=ingestion_batch_id,
            )
        )


def _delete_existing_curated_source_rows(db: Session, patient: Patient, source_system_id: int) -> None:
    records = _patient_curated_records(patient)
    for table_name, record_ids in records:
        if not record_ids:
            continue
        (
            db.query(CuratedRecordSource)
            .filter(
                CuratedRecordSource.source_system_id == source_system_id,
                CuratedRecordSource.curated_table_name == table_name,
                CuratedRecordSource.curated_record_id.in_(record_ids),
            )
            .delete(synchronize_session=False)
        )


def _patient_curated_records(patient: Patient) -> List[Tuple[str, List[int]]]:
    return [
        ("patients", [patient.id]),
        ("conditions", _ids(patient.conditions)),
        ("observations", _ids(patient.observations)),
        ("encounters", _ids(patient.encounters)),
        ("medication_requests", _ids(patient.medication_requests)),
        ("allergy_intolerances", _ids(patient.allergies)),
    ]


def _ids(records: Iterable[Any]) -> List[int]:
    return [record.id for record in records if record.id is not None]


def _add_curated_source(
    db: Session,
    curated_table_name: str,
    curated_record_id: int,
    source_system_id: int,
    ingestion_batch_id: int,
    raw_record_id: Optional[str] = None,
) -> None:
    db.add(
        CuratedRecordSource(
            curated_table_name=curated_table_name,
            curated_record_id=curated_record_id,
            source_system_id=source_system_id,
            ingestion_batch_id=ingestion_batch_id,
            raw_table_name="fhir_bundle",
            raw_record_id=raw_record_id,
            transform_version=FHIR_UPLOAD_TRANSFORM_VERSION,
        )
    )
