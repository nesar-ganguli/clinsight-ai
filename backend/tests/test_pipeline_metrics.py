from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.pipeline_run import PipelineRun
from app.services.pipeline_runs import start_pipeline_run
from scripts.report_pipeline_metrics import (
    CLINICAL_TABLES,
    RAW_TABLES,
    collect_pipeline_metrics,
    count_raw_pipeline_records,
    finalize_pipeline_run,
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
        raw_record_count = count_raw_pipeline_records(db, "batch-1")

    assert metrics["status"] == "completed"
    assert metrics["raw_counts"]["raw_patients"] == 1
    assert metrics["raw_counts"]["raw_encounters"] == 2
    assert metrics["raw_total"] == 3
    assert raw_record_count == 3
    assert metrics["clinical_counts"]["patients"] == 1
    assert metrics["clinical_counts"]["conditions"] == 2
    assert metrics["clinical_total"] == 3


def test_pipeline_metrics_finalize_the_durable_airflow_run():
    engine = create_engine("sqlite://")
    PipelineRun.__table__.create(engine)
    with engine.begin() as connection:
        for table_name in RAW_TABLES:
            connection.execute(text(f"create table {table_name} (ingestion_batch_id text)"))
        for table_name in CLINICAL_TABLES:
            connection.execute(
                text(f"create table clinical_{table_name} (ingestion_batch_id text)")
            )
        connection.execute(
            text("insert into raw_patients (ingestion_batch_id) values ('batch-observed')")
        )
        connection.execute(
            text("insert into clinical_patients (ingestion_batch_id) values ('batch-observed')")
        )

    with Session(engine) as db:
        start_pipeline_run(
            db,
            pipeline_name="clinsight_hospital_pipeline",
            run_id="manual__observed",
            source_system="internal_hospital_ods",
            batch_id="batch-observed",
        )
        metrics = finalize_pipeline_run(
            db,
            run_id="manual__observed",
            ingestion_batch_id="batch-observed",
        )
        pipeline_run = db.query(PipelineRun).one()

        assert metrics["raw_total"] == 1
        assert metrics["clinical_total"] == 1
        assert pipeline_run.status == "success"
        assert pipeline_run.batch_id == "batch-observed"
        assert pipeline_run.received_count == 1
        assert pipeline_run.accepted_count == 1
        assert pipeline_run.rejected_count == 0
        assert pipeline_run.duration_ms is not None
