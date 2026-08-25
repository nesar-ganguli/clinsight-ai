from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from scripts.report_pipeline_metrics import (
    CLINICAL_TABLES,
    RAW_TABLES,
    collect_pipeline_metrics,
)


def test_pipeline_metrics_reports_batch_scoped_raw_and_clinical_counts():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for table_name in RAW_TABLES:
            connection.execute(text(f"create table {table_name} (ingestion_batch_id text)"))
        for table_name in CLINICAL_TABLES:
            connection.execute(
                text(f"create table clinical_{table_name} (ingestion_batch_id text)")
            )

        connection.execute(
            text("insert into raw_patients (ingestion_batch_id) values ('batch-1'), ('batch-2')")
        )
        connection.execute(
            text("insert into raw_encounters (ingestion_batch_id) values ('batch-1'), ('batch-1')")
        )
        connection.execute(
            text("insert into clinical_patients (ingestion_batch_id) values ('batch-1')")
        )
        connection.execute(
            text("insert into clinical_conditions (ingestion_batch_id) values ('batch-1'), ('batch-1')")
        )

    with Session(engine) as db:
        metrics = collect_pipeline_metrics(db, "batch-1")

    assert metrics["status"] == "completed"
    assert metrics["raw_counts"]["raw_patients"] == 1
    assert metrics["raw_counts"]["raw_encounters"] == 2
    assert metrics["raw_total"] == 3
    assert metrics["clinical_counts"]["patients"] == 1
    assert metrics["clinical_counts"]["conditions"] == 2
    assert metrics["clinical_total"] == 3
