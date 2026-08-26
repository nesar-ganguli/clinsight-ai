import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.services.pipeline_runs import log_stage_event


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a command and emit structured pipeline stage logs."
    )
    parser.add_argument("--pipeline-name", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--batch-id")
    parser.add_argument("--stage", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command is required after --")
    return args


def run_observed_command(args: argparse.Namespace) -> int:
    started = time.monotonic()
    log_stage_event(
        pipeline_name=args.pipeline_name,
        run_id=args.run_id,
        batch_id=args.batch_id,
        stage=args.stage,
        status="started",
    )
    completed = subprocess.run(args.command, check=False)
    duration_ms = int((time.monotonic() - started) * 1000)
    status = "success" if completed.returncode == 0 else "failed"
    log_stage_event(
        pipeline_name=args.pipeline_name,
        run_id=args.run_id,
        batch_id=args.batch_id,
        stage=args.stage,
        status=status,
        duration_ms=duration_ms,
        error_message=(
            None
            if completed.returncode == 0
            else f"Command exited with status {completed.returncode}"
        ),
    )
    return completed.returncode


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(run_observed_command(parse_args()))


if __name__ == "__main__":
    main()
