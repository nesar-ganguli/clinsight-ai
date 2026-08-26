from datetime import datetime, timezone
import subprocess

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param

from pipeline_definition import (
    DAG_ID,
    DEFAULT_RETRIES,
    RETRY_DELAY,
    TASK_DEFINITIONS,
    TASK_DEPENDENCIES,
)


def record_pipeline_failure(context):
    run_id = context["run_id"]
    configured_batch_id = context.get("params", {}).get("batch_id")
    batch_id = configured_batch_id or run_id
    task_instance = context.get("task_instance")
    task_id = task_instance.task_id if task_instance else "unknown"
    subprocess.run(
        [
            "python",
            "/opt/clinsight/backend/scripts/manage_pipeline_run.py",
            "fail",
            "--pipeline-name",
            DAG_ID,
            "--run-id",
            run_id,
            "--source-system",
            "internal_hospital_ods",
            "--batch-id",
            batch_id,
            "--error-message",
            f"Airflow task {task_id} failed after retries",
        ],
        check=False,
    )


with DAG(
    dag_id=DAG_ID,
    description="Generate synthetic hospital data and build/test ClinSight dbt clinical marts.",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": DEFAULT_RETRIES,
        "retry_delay": RETRY_DELAY,
        "on_failure_callback": record_pipeline_failure,
    },
    params={
        "batch_id": Param(
            default="",
            type="string",
            description="Optional source batch ID; the Airflow run ID is used when omitted.",
        ),
        "patient_count": Param(
            default=1000,
            type="integer",
            minimum=1,
            description="Number of deterministic synthetic patients to generate.",
        ),
        "seed": Param(
            default=42,
            type="integer",
            description="Deterministic synthetic-data random seed.",
        ),
    },
    tags=["clinsight", "synthetic", "dbt"],
) as dag:
    tasks = {
        task_id: BashOperator(
            task_id=task_id,
            bash_command=definition["bash_command"],
            env=definition["env"],
            append_env=True,
        )
        for task_id, definition in TASK_DEFINITIONS.items()
    }

    for upstream_task_id, downstream_task_id in TASK_DEPENDENCIES:
        tasks[upstream_task_id] >> tasks[downstream_task_id]
