import argparse
import json
import logging
from types import SimpleNamespace

from scripts.observe_pipeline_command import parse_args, run_observed_command


def test_observed_command_parser_removes_argument_separator(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "observe_pipeline_command.py",
            "--pipeline-name",
            "pipeline",
            "--run-id",
            "run",
            "--stage",
            "dbt_run",
            "--",
            "dbt",
            "run",
        ],
    )

    assert parse_args().command == ["dbt", "run"]


def test_observed_command_logs_structured_success_and_duration(monkeypatch, caplog):
    timestamps = iter([10.0, 10.125])
    monkeypatch.setattr("scripts.observe_pipeline_command.time.monotonic", lambda: next(timestamps))
    monkeypatch.setattr(
        "scripts.observe_pipeline_command.subprocess.run",
        lambda command, check: SimpleNamespace(returncode=0),
    )
    args = argparse.Namespace(
        pipeline_name="clinsight_hospital_pipeline",
        run_id="manual__test",
        batch_id="batch-test",
        stage="dbt_run",
        command=["dbt", "run"],
    )

    with caplog.at_level(logging.INFO, logger="app.services.pipeline_runs"):
        return_code = run_observed_command(args)

    events = [json.loads(record.message) for record in caplog.records]
    assert return_code == 0
    assert events[0]["status"] == "started"
    assert events[1]["status"] == "success"
    assert events[1]["stage"] == "dbt_run"
    assert events[1]["duration_ms"] == 125


def test_observed_command_propagates_failure_and_logs_exit_status(monkeypatch, caplog):
    timestamps = iter([20.0, 20.25])
    monkeypatch.setattr("scripts.observe_pipeline_command.time.monotonic", lambda: next(timestamps))
    monkeypatch.setattr(
        "scripts.observe_pipeline_command.subprocess.run",
        lambda command, check: SimpleNamespace(returncode=2),
    )
    args = argparse.Namespace(
        pipeline_name="clinsight_hospital_pipeline",
        run_id="manual__failed",
        batch_id="batch-failed",
        stage="dbt_test",
        command=["dbt", "test"],
    )

    with caplog.at_level(logging.INFO, logger="app.services.pipeline_runs"):
        return_code = run_observed_command(args)

    event = json.loads(caplog.records[-1].message)
    assert return_code == 2
    assert event["status"] == "failed"
    assert event["stage"] == "dbt_test"
    assert event["duration_ms"] == 250
    assert event["error_message"] == "Command exited with status 2"
