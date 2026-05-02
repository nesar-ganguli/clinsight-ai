from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import inspect, or_, text
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.patient import Patient


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
    app_patients = _list_app_patient_summaries(db, search) if ingestion_batch_id is None else []
    dbt_patients = _list_dbt_patient_summaries(db, search, ingestion_batch_id)
    patients_by_id = {patient.id: patient for patient in dbt_patients}
    patients_by_id.update({patient.id: patient for patient in app_patients})
    patients = sorted(patients_by_id.values(), key=lambda patient: patient.id, reverse=True)

    return {
        "items": patients[offset:offset + limit],
        "total": len(patients),
        "limit": limit,
        "offset": offset,
    }


def get_patient_record(db: Session, patient_id: int):
    app_patient = _get_app_patient(db, patient_id)
    if app_patient:
        return app_patient

    return _get_dbt_patient(db, patient_id)


def _list_app_patient_summaries(db: Session, search: Optional[str]) -> List[Any]:
    query = db.query(Patient)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Patient.full_name.ilike(search_term),
                Patient.fhir_patient_id.ilike(search_term),
            )
        )
    return query.all()


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


def _list_dbt_patient_summaries(
    db: Session,
    search: Optional[str],
    ingestion_batch_id: Optional[str] = None,
) -> List[Any]:
    if not _clinical_table_exists(db, "patients"):
        return []

    sql = f"""
        select
            id,
            fhir_patient_id,
            full_name,
            gender,
            birth_date,
            ingestion_batch_id,
            source_patient_id
        from {_clinical_table_name(db, "patients")}
    """
    params: Dict[str, Any] = {}
    filters = []
    if search:
        if db.bind.dialect.name == "sqlite":
            filters.append("""
                (
                    lower(coalesce(full_name, '')) like lower(:search_term)
                    or cast(id as text) like :search_term
                    or lower(coalesce(source_patient_id, '')) like lower(:search_term)
                )
            """)
        else:
            filters.append("""
                (
                    full_name ilike :search_term
                    or cast(id as text) ilike :search_term
                    or coalesce(source_patient_id, '') ilike :search_term
                )
            """)
        params["search_term"] = f"%{search.strip()}%"
    if ingestion_batch_id:
        filters.append("ingestion_batch_id = :ingestion_batch_id")
        params["ingestion_batch_id"] = ingestion_batch_id
    if filters:
        sql += " where " + " and ".join(filters)

    rows = db.execute(text(sql), params).mappings().all()
    return [_namespace(row) for row in rows]


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
                ingestion_batch_id,
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
        "onset_date": _as_text(row.get("onset_date")),
    }


def _observation_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "fhir_observation_id": row.get("fhir_observation_id"),
        "observation_code": row.get("observation_code"),
        "observation_name": row.get("observation_name"),
        "value": row.get("value"),
        "unit": row.get("unit"),
        "effective_date": _as_text(row.get("effective_date")),
    }


def _encounter_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "fhir_encounter_id": row.get("fhir_encounter_id"),
        "status": row.get("status"),
        "encounter_class": row.get("encounter_class"),
        "encounter_type": row.get("encounter_type"),
        "period_start": _as_text(row.get("period_start")),
        "period_end": _as_text(row.get("period_end")),
    }


def _medication_row(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "fhir_medication_request_id": row.get("fhir_medication_request_id"),
        "status": row.get("status"),
        "intent": row.get("intent"),
        "medication_code": row.get("medication_code"),
        "medication_name": row.get("medication_name"),
        "authored_on": _as_text(row.get("authored_on")),
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
        "recorded_date": _as_text(row.get("recorded_date")),
    }


def _namespace(row: Any) -> SimpleNamespace:
    return SimpleNamespace(**{key: _as_text(value) for key, value in dict(row).items()})


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
