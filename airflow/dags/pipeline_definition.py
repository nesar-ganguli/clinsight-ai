from datetime import timedelta


DAG_ID = "clinsight_hospital_pipeline"
DEFAULT_RETRIES = 2
RETRY_DELAY = timedelta(minutes=5)

TASK_DEFINITIONS = {
    "start_pipeline_run": {
        "bash_command": """set -euo pipefail
cd /opt/clinsight/backend
alembic upgrade head
python scripts/manage_pipeline_run.py start \
  --pipeline-name clinsight_hospital_pipeline \
  --run-id "$PIPELINE_RUN_ID" \
  --source-system internal_hospital_ods \
  --batch-id "$PIPELINE_BATCH_ID"
""",
        "env": {
            "PIPELINE_RUN_ID": "{{ run_id }}",
            "PIPELINE_BATCH_ID": "{{ params.batch_id if params.batch_id else run_id }}",
        },
    },
    "generate_hospital_data": {
        "bash_command": """set -euo pipefail
cd /opt/clinsight/backend
alembic upgrade head
python scripts/generate_hospital_data.py \
  --patients "$HOSPITAL_PATIENTS" \
  --seed "$HOSPITAL_SEED" \
  --ingestion-batch-id "$PIPELINE_BATCH_ID"
""",
        "env": {
            "HOSPITAL_PATIENTS": "{{ params.patient_count }}",
            "HOSPITAL_SEED": "{{ params.seed }}",
            "PIPELINE_BATCH_ID": "{{ params.batch_id if params.batch_id else run_id }}",
        },
    },
    "dbt_run": {
        "bash_command": """set -euo pipefail
cd /opt/clinsight/dbt
cp profiles.example.yml profiles.yml
python /opt/clinsight/backend/scripts/observe_pipeline_command.py \
  --pipeline-name clinsight_hospital_pipeline \
  --run-id "$PIPELINE_RUN_ID" \
  --batch-id "$PIPELINE_BATCH_ID" \
  --stage dbt_run \
  -- dbt run --profiles-dir . --select "$DBT_SELECT"
""",
        "env": {
            "PIPELINE_RUN_ID": "{{ run_id }}",
            "PIPELINE_BATCH_ID": "{{ params.batch_id if params.batch_id else run_id }}",
        },
    },
    "dbt_test": {
        "bash_command": """set -euo pipefail
cd /opt/clinsight/dbt
cp profiles.example.yml profiles.yml
python /opt/clinsight/backend/scripts/observe_pipeline_command.py \
  --pipeline-name clinsight_hospital_pipeline \
  --run-id "$PIPELINE_RUN_ID" \
  --batch-id "$PIPELINE_BATCH_ID" \
  --stage dbt_test \
  -- dbt test --profiles-dir . --select "$DBT_SELECT"
""",
        "env": {
            "PIPELINE_RUN_ID": "{{ run_id }}",
            "PIPELINE_BATCH_ID": "{{ params.batch_id if params.batch_id else run_id }}",
        },
    },
    "record_pipeline_metrics": {
        "bash_command": """set -euo pipefail
cd /opt/clinsight/backend
python scripts/report_pipeline_metrics.py \
  --ingestion-batch-id "$PIPELINE_BATCH_ID" \
  --run-id "$PIPELINE_RUN_ID"
""",
        "env": {
            "PIPELINE_RUN_ID": "{{ run_id }}",
            "PIPELINE_BATCH_ID": "{{ params.batch_id if params.batch_id else run_id }}",
        },
    },
}

TASK_DEPENDENCIES = (
    ("start_pipeline_run", "generate_hospital_data"),
    ("generate_hospital_data", "dbt_run"),
    ("dbt_run", "dbt_test"),
    ("dbt_test", "record_pipeline_metrics"),
)
