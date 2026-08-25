from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.temporal import parse_fhir_datetime
from app.models.patient import Patient
from app.repositories.patient_directory import list_patient_summaries


CLINICAL_TABLES = {
    "patients": "patients",
    "conditions": "conditions",
    "observations": "observations",
    "encounters": "encounters",
    "medication_requests": "medication_requests",
    "allergies": "allergies",
}


def list_patient_records(
    db: Session,
    search: Optional[str] = None,
    ingestion_batch_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    clinical_patient_table = (
        _clinical_table_name(db, "patients")
        if _clinical_table_exists(db, "patients")
        else None
    )
    patient_rows, total = list_patient_summaries(
        db,
        clinical_patient_table=clinical_patient_table,
        search=search,
        ingestion_batch_id=ingestion_batch_id,
        limit=limit,
        offset=offset,
    )

    return {
        "items": [_namespace(row) for row in patient_rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_patient_record(db: Session, patient_id: int):
    app_patient = _get_app_patient(db, patient_id)
    if app_patient:
        return app_patient

    return _get_dbt_patient(db, patient_id)


def _get_app_patient(db: Session, patient_id: int):
    return (
        db.query(Patient)
        .options(
            joinedload(Patient.conditions),
            joinedload(Patient.observations),
            joinedload(Patient.encounters),
            joinedload(Patient.medication_requests),
            joinedload(Patient.allergies),
        )
        .filter(Patient.id == patient_id)
        .first()
    )


def _get_dbt_patient(db: Session, patient_id: int):
    if not _clinical_table_exists(db, "patients"):
        return None

    rows = db.execute(
        text(
            f"""
            select
                id,
                fhir_patient_id,
                full_name,
                gender,
                birth_date,
                source_type,
                source_system,
                source_record_id,
                ingestion_batch_id,
                transformed_at,
                source_patient_id
            from {_clinical_table_name(db, "patients")}
            where id = :patient_id
            """
        ),
        {"patient_id": patient_id},
    ).mappings().all()
    if not rows:
        return None

    patient = _namespace(rows[0])
    patient.conditions = _get_dbt_children(db, "conditions", patient_id, _condition_row)
    patient.observations = _get_dbt_children(db, "observations", patient_id, _observation_row)
    patient.encounters = _get_dbt_children(db, "encounters", patient_id, _encounter_row)
    patient.medication_requests = _get_dbt_children(db, "medication_requests", patient_id, _medication_row)
    patient.allergies = _get_dbt_children(db, "allergies", patient_id, _allergy_row)
    return patient


def _get_dbt_children(db: Session, table_key: str, patient_id: int, mapper) -> List[Any]:
    if not _clinical_table_exists(db, table_key):
        return []

    rows = db.execute(
        text(
            f"""
            select *
            from {_clinical_table_name(db, table_key)}
            where patient_id = :patient_id
            order by id
            """
        ),
        {"patient_id": patient_id},
    ).mappings().all()
    return [_namespace(mapper(row)) for row in rows]


def _condition_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "fhir_condition_id": row.get("fhir_condition_id"),
        "condition_code": row.get("condition_code"),
        "condition_name": row.get("condition_name"),
        "clinical_status": row.get("clinical_status"),
        "onset_date": parse_fhir_datetime(row.get("onset_date")),
        **_source_metadata(row),
    }


def _observation_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "fhir_observation_id": row.get("fhir_observation_id"),
        "observation_code": row.get("observation_code"),
        "observation_name": row.get("observation_name"),
        "value": row.get("value"),
        "unit": row.get("unit"),
        "effective_date": parse_fhir_datetime(row.get("effective_date")),
        **_source_metadata(row),
    }


def _encounter_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "fhir_encounter_id": row.get("fhir_encounter_id"),
        "status": row.get("status"),
        "encounter_class": row.get("encounter_class"),
        "encounter_type": row.get("encounter_type"),
        "period_start": parse_fhir_datetime(row.get("period_start")),
        "period_end": parse_fhir_datetime(row.get("period_end")),
        **_source_metadata(row),
    }


def _medication_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "fhir_medication_request_id": row.get("fhir_medication_request_id"),
        "status": row.get("status"),
        "intent": row.get("intent"),
        "medication_code": row.get("medication_code"),
        "medication_name": row.get("medication_name"),
        "authored_on": parse_fhir_datetime(row.get("authored_on")),
        **_source_metadata(row),
    }


def _allergy_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "fhir_allergy_id": row.get("fhir_allergy_id"),
        "clinical_status": row.get("clinical_status"),
        "verification_status": row.get("verification_status"),
        "allergy_code": row.get("allergy_code"),
        "allergy_name": row.get("allergy_name"),
        "criticality": row.get("criticality"),
        "recorded_date": parse_fhir_datetime(row.get("recorded_date")),
        **_source_metadata(row),
    }


def _source_metadata(row) -> Dict[str, Any]:
    return {
        "source_type": row.get("source_type"),
        "source_system": row.get("source_system"),
        "source_record_id": row.get("source_record_id"),
        "ingestion_batch_id": row.get("ingestion_batch_id"),
        "transformed_at": _as_text(row.get("transformed_at")),
    }


def _namespace(row: Any) -> SimpleNamespace:
    return SimpleNamespace(
        **{
            key: value.isoformat() if isinstance(value, date) and not isinstance(value, datetime) else value
            for key, value in dict(row).items()
        }
    )


def _as_text(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _clinical_table_exists(db: Session, table_key: str) -> bool:
    schema, table_name = _clinical_table_parts(db, table_key)
    return inspect(db.bind).has_table(table_name, schema=schema)


def _clinical_table_name(db: Session, table_key: str) -> str:
    schema, table_name = _clinical_table_parts(db, table_key)
    if schema:
        return f'"{schema}"."{table_name}"'
    return f'"{table_name}"'


def _clinical_table_parts(db: Session, table_key: str) -> Tuple[Optional[str], str]:
    table_name = CLINICAL_TABLES[table_key]
    if db.bind.dialect.name == "sqlite":
        return None, f"clinical_{table_name}"
    return settings.clinical_schema, table_name
