import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal


RAW_TABLES = (
    "raw_patients",
    "raw_encounters",
    "raw_diagnoses",
    "raw_labs",
    "raw_medications",
    "raw_allergies",
    "raw_providers",
    "raw_departments",
)
CLINICAL_TABLES = (
    "patients",
    "conditions",
    "observations",
    "encounters",
    "medication_requests",
    "allergies",
)


def collect_pipeline_metrics(db: Session, ingestion_batch_id: str) -> Dict[str, Any]:
    raw_counts = {
        table_name: _count_batch_rows(db, table_name, ingestion_batch_id)
        for table_name in RAW_TABLES
    }
    clinical_counts = {
        table_name: _count_batch_rows(
            db,
            _clinical_table_name(db, table_name),
            ingestion_batch_id,
            schema=_clinical_schema(db),
        )
        for table_name in CLINICAL_TABLES
    }

    return {
        "pipeline_name": "clinsight_hospital_pipeline",
        "ingestion_batch_id": ingestion_batch_id,
        "status": "completed",
        "raw_counts": raw_counts,
        "clinical_counts": clinical_counts,
        "raw_total": sum(raw_counts.values()),
        "clinical_total": sum(clinical_counts.values()),
    }


def _count_batch_rows(
    db: Session,
    table_name: str,
    ingestion_batch_id: str,
    schema: Optional[str] = None,
) -> int:
    if not inspect(db.bind).has_table(table_name, schema=schema):
        qualified_name = f"{schema}.{table_name}" if schema else table_name
        raise RuntimeError(f"Required pipeline table is missing: {qualified_name}")

    preparer = db.bind.dialect.identifier_preparer
    qualified_table_name = preparer.quote(table_name)
    if schema:
        qualified_table_name = f"{preparer.quote_schema(schema)}.{qualified_table_name}"

    return int(
        db.execute(
            text(
                f"select count(*) from {qualified_table_name} "
                "where ingestion_batch_id = :ingestion_batch_id"
            ),
            {"ingestion_batch_id": ingestion_batch_id},
        ).scalar_one()
    )


def _clinical_schema(db: Session) -> Optional[str]:
    return settings.clinical_schema if db.bind.dialect.name != "sqlite" else None


def _clinical_table_name(db: Session, table_name: str) -> str:
    return table_name if db.bind.dialect.name != "sqlite" else f"clinical_{table_name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report batch-scoped raw and dbt clinical record counts to stdout."
    )
    parser.add_argument("--ingestion-batch-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        metrics = collect_pipeline_metrics(db, args.ingestion_batch_id)
    finally:
        db.close()
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
