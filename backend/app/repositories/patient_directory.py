from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


PATIENT_RESULT_COLUMNS = """
    id,
    fhir_patient_id,
    full_name,
    gender,
    birth_date,
    source_type,
    source_system,
    source_record_id,
    ingestion_batch_id,
    transformed_at
"""


def list_patient_summaries(
    db: Session,
    *,
    clinical_patient_table: Optional[str],
    search: Optional[str],
    ingestion_batch_id: Optional[str],
    limit: int,
    offset: int,
) -> Tuple[List[Dict[str, Any]], int]:
    normalized_search = search.strip() if search and search.strip() else None
    params: Dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }
    if normalized_search:
        params["search_term"] = f"%{normalized_search}%"
    if ingestion_batch_id:
        params["ingestion_batch_id"] = ingestion_batch_id

    source_queries = []
    if ingestion_batch_id is None:
        source_queries.append(_application_patient_query(normalized_search is not None))
    if clinical_patient_table:
        source_queries.append(
            _dbt_patient_query(
                clinical_patient_table,
                has_search=normalized_search is not None,
                has_ingestion_batch=ingestion_batch_id is not None,
            )
        )

    if not source_queries:
        return [], 0

    directory_cte = _directory_cte("\nUNION ALL\n".join(source_queries))
    total = int(
        db.execute(
            text(f"{directory_cte} SELECT count(*) FROM deduplicated_patients"),
            params,
        ).scalar_one()
    )
    rows = (
        db.execute(
            text(
                f"""
                {directory_cte}
                SELECT {PATIENT_RESULT_COLUMNS}
                FROM deduplicated_patients
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows], total


def _application_patient_query(has_search: bool) -> str:
    where_clause = ""
    if has_search:
        where_clause = """
            WHERE (
                lower(coalesce(p.full_name, '')) LIKE lower(:search_term)
                OR cast(p.id AS text) LIKE :search_term
                OR lower(coalesce(p.fhir_patient_id, '')) LIKE lower(:search_term)
                OR lower(coalesce(p.source_record_id, '')) LIKE lower(:search_term)
                OR EXISTS (
                    SELECT 1
                    FROM patient_source_identifiers psi
                    WHERE psi.patient_id = p.id
                      AND lower(psi.identifier_value) LIKE lower(:search_term)
                )
            )
        """

    return f"""
        SELECT
            p.id,
            p.fhir_patient_id,
            p.full_name,
            p.gender,
            cast(p.birth_date AS text) AS birth_date,
            p.source_type,
            p.source_system,
            p.source_record_id,
            p.ingestion_batch_id,
            p.transformed_at,
            1 AS source_priority
        FROM patients p
        {where_clause}
    """


def _dbt_patient_query(
    clinical_patient_table: str,
    *,
    has_search: bool,
    has_ingestion_batch: bool,
) -> str:
    filters = []
    if has_search:
        filters.append(
            """
            (
                lower(coalesce(d.full_name, '')) LIKE lower(:search_term)
                OR cast(d.id AS text) LIKE :search_term
                OR lower(coalesce(d.fhir_patient_id, '')) LIKE lower(:search_term)
                OR lower(coalesce(d.source_patient_id, '')) LIKE lower(:search_term)
                OR lower(coalesce(d.source_record_id, '')) LIKE lower(:search_term)
            )
            """
        )
    if has_ingestion_batch:
        filters.append("d.ingestion_batch_id = :ingestion_batch_id")
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    return f"""
        SELECT
            d.id,
            d.fhir_patient_id,
            d.full_name,
            d.gender,
            cast(d.birth_date AS text) AS birth_date,
            d.source_type,
            d.source_system,
            d.source_record_id,
            d.ingestion_batch_id,
            d.transformed_at,
            0 AS source_priority
        FROM {clinical_patient_table} d
        {where_clause}
    """


def _directory_cte(source_query: str) -> str:
    return f"""
        WITH patient_sources AS (
            {source_query}
        ),
        ranked_patients AS (
            SELECT
                patient_sources.*,
                row_number() OVER (
                    PARTITION BY id
                    ORDER BY source_priority DESC
                ) AS source_rank
            FROM patient_sources
        ),
        deduplicated_patients AS (
            SELECT {PATIENT_RESULT_COLUMNS}
            FROM ranked_patients
            WHERE source_rank = 1
        )
    """
