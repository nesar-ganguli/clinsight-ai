import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.pipeline_run import PipelineRun
from app.services.pipeline_runs import summarize_pipeline_runs


def serialize_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    serialized = dict(metrics)
    latest = serialized.get("latest_successful_run")
    if isinstance(latest, PipelineRun):
        serialized["latest_successful_run"] = {
            "pipeline_name": latest.pipeline_name,
            "run_id": latest.run_id,
            "source_system": latest.source_system,
            "batch_id": latest.batch_id,
            "completed_at": latest.completed_at.isoformat() if latest.completed_at else None,
        }
    return serialized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize durable pipeline-run metrics.")
    parser.add_argument("--pipeline-name")
    parser.add_argument("--source-system")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        metrics = summarize_pipeline_runs(
            db,
            pipeline_name=args.pipeline_name,
            source_system=args.source_system,
        )
        output = serialize_metrics(metrics)
    finally:
        db.close()
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
