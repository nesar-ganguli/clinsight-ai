import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.services.pipeline_runs import fail_pipeline_run, start_pipeline_run
from scripts.report_pipeline_metrics import count_raw_pipeline_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start or fail a durable pipeline run.")
    subparsers = parser.add_subparsers(dest="action", required=True)

    for action in ("start", "fail"):
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument("--pipeline-name", required=True)
        action_parser.add_argument("--run-id", required=True)
        action_parser.add_argument("--source-system")
        action_parser.add_argument("--batch-id")
        action_parser.add_argument("--received-count", type=int)

    subparsers.choices["fail"].add_argument(
        "--error-message",
        default="Airflow pipeline task failed",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    db = SessionLocal()
    try:
        if args.action == "start":
            pipeline_run = start_pipeline_run(
                db,
                pipeline_name=args.pipeline_name,
                run_id=args.run_id,
                source_system=args.source_system,
                batch_id=args.batch_id,
                received_count=args.received_count or 0,
            )
        else:
            received_count = args.received_count
            if received_count is None and args.batch_id:
                try:
                    received_count = count_raw_pipeline_records(db, args.batch_id)
                except RuntimeError:
                    received_count = 0
            pipeline_run = fail_pipeline_run(
                db,
                pipeline_name=args.pipeline_name,
                run_id=args.run_id,
                source_system=args.source_system,
                batch_id=args.batch_id,
                received_count=received_count,
                error_message=args.error_message,
            )
    finally:
        db.close()

    print(json.dumps({
        "pipeline_name": pipeline_run.pipeline_name,
        "run_id": pipeline_run.run_id,
        "batch_id": pipeline_run.batch_id,
        "status": pipeline_run.status,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
