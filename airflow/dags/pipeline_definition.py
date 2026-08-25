from datetime import timedelta


DAG_ID = "clinsight_hospital_pipeline"
DEFAULT_RETRIES = 2
RETRY_DELAY = timedelta(minutes=5)

TASK_DEFINITIONS = {
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
dbt run --profiles-dir . --select "$DBT_SELECT"
""",
        "env": {},
    },
    "dbt_test": {
        "bash_command": """set -euo pipefail
cd /opt/clinsight/dbt
cp profiles.example.yml profiles.yml
dbt test --profiles-dir . --select "$DBT_SELECT"
""",
        "env": {},
    },
    "record_pipeline_metrics": {
        "bash_command": """set -euo pipefail
cd /opt/clinsight/backend
python scripts/report_pipeline_metrics.py \
  --ingestion-batch-id "$PIPELINE_BATCH_ID"
""",
        "env": {
            "PIPELINE_BATCH_ID": "{{ params.batch_id if params.batch_id else run_id }}",
        },
    },
}

TASK_DEPENDENCIES = (
    ("generate_hospital_data", "dbt_run"),
    ("dbt_run", "dbt_test"),
    ("dbt_test", "record_pipeline_metrics"),
)
