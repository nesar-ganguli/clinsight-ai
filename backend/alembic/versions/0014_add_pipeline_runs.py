"""Add durable operational pipeline runs.

Revision ID: 0014_pipeline_runs
Revises: 0013_patient_directory_indexes
Create Date: 2026-08-25 00:00:00
"""

import sqlalchemy as sa
from alembic import op


revision = "0014_pipeline_runs"
down_revision = "0013_patient_directory_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pipeline_name", sa.String(length=100), nullable=False),
        sa.Column("run_id", sa.String(length=255), nullable=False),
        sa.Column("source_system", sa.String(length=255), nullable=True),
        sa.Column("batch_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="processing", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("received_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("accepted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rejected_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicate_or_updated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_name", "run_id", name="uq_pipeline_runs_pipeline_run"),
    )
    for column_name in (
        "id",
        "pipeline_name",
        "run_id",
        "source_system",
        "batch_id",
        "status",
        "started_at",
    ):
        op.create_index(
            op.f(f"ix_pipeline_runs_{column_name}"),
            "pipeline_runs",
            [column_name],
        )


def downgrade() -> None:
    for column_name in reversed((
        "id",
        "pipeline_name",
        "run_id",
        "source_system",
        "batch_id",
        "status",
        "started_at",
    )):
        op.drop_index(op.f(f"ix_pipeline_runs_{column_name}"), table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
