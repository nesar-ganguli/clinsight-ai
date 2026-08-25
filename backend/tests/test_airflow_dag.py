import importlib.util
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AIRFLOW_DAGS_DIR = REPOSITORY_ROOT / "airflow" / "dags"


def load_pipeline_definition():
    path = AIRFLOW_DAGS_DIR / "pipeline_definition.py"
    spec = importlib.util.spec_from_file_location("clinsight_pipeline_definition", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_airflow_pipeline_has_required_retryable_task_chain():
    definition = load_pipeline_definition()

    assert definition.DAG_ID == "clinsight_hospital_pipeline"
    assert tuple(definition.TASK_DEFINITIONS) == (
        "generate_hospital_data",
        "dbt_run",
        "dbt_test",
        "record_pipeline_metrics",
    )
    assert definition.TASK_DEPENDENCIES == (
        ("generate_hospital_data", "dbt_run"),
        ("dbt_run", "dbt_test"),
        ("dbt_test", "record_pipeline_metrics"),
    )
    assert definition.DEFAULT_RETRIES == 2
    assert definition.RETRY_DELAY.total_seconds() == 300


def test_airflow_tasks_reuse_existing_commands_and_propagate_failures():
    definition = load_pipeline_definition()
    commands = {
        task_id: task_definition["bash_command"]
        for task_id, task_definition in definition.TASK_DEFINITIONS.items()
    }

    assert all(command.startswith("set -euo pipefail") for command in commands.values())
    assert "scripts/generate_hospital_data.py" in commands["generate_hospital_data"]
    assert "--ingestion-batch-id \"$PIPELINE_BATCH_ID\"" in commands["generate_hospital_data"]
    assert "dbt run" in commands["dbt_run"]
    assert "dbt test" in commands["dbt_test"]
    assert "scripts/report_pipeline_metrics.py" in commands["record_pipeline_metrics"]
    assert "run_id" in definition.TASK_DEFINITIONS["generate_hospital_data"]["env"][
        "PIPELINE_BATCH_ID"
    ]
    assert definition.TASK_DEFINITIONS["record_pipeline_metrics"]["env"][
        "PIPELINE_BATCH_ID"
    ] == definition.TASK_DEFINITIONS["generate_hospital_data"]["env"]["PIPELINE_BATCH_ID"]


def test_airflow_dag_and_optional_compose_profile_are_declared():
    dag_path = AIRFLOW_DAGS_DIR / "clinsight_hospital_pipeline.py"
    compile(dag_path.read_text(encoding="utf-8"), str(dag_path), "exec")

    compose_text = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile_text = (REPOSITORY_ROOT / "airflow" / "Dockerfile").read_text(encoding="utf-8")

    assert "  airflow:" in compose_text
    assert "      - airflow" in compose_text
    assert "command: standalone" in compose_text
    assert "apache/airflow:3.3.1-python3.11" in dockerfile_text
