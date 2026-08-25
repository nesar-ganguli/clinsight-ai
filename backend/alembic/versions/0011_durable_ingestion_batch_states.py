"""Persist durable ingestion batch lifecycle states.

Revision ID: 0011_durable_batch_states
Revises: 0010_typed_clinical_dates
Create Date: 2026-08-25 00:00:00
"""

import sqlalchemy as sa
from alembic import op


revision = "0011_durable_batch_states"
down_revision = "0010_typed_clinical_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ingestion_batches") as batch_op:
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("accepted_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("rejected_count", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE ingestion_batches
            SET started_at = received_at,
                completed_at = processed_at,
                error_message = error_summary,
                accepted_count = CASE WHEN status = 'processed' THEN record_count ELSE 0 END,
                rejected_count = CASE WHEN status = 'processed' THEN 0 ELSE record_count END,
                status = CASE WHEN status = 'processed' THEN 'success' ELSE status END
            """
        )
    )

    with op.batch_alter_table("ingestion_batches") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=100),
            existing_nullable=False,
            server_default="processing",
        )
        batch_op.alter_column(
            "started_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        batch_op.alter_column(
            "accepted_count",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="0",
        )
        batch_op.alter_column(
            "rejected_count",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="0",
        )
        batch_op.drop_column("error_summary")
        batch_op.drop_column("processed_at")
        batch_op.drop_column("received_at")


def downgrade() -> None:
    with op.batch_alter_table("ingestion_batches") as batch_op:
        batch_op.add_column(sa.Column("received_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("error_summary", sa.Text(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE ingestion_batches
            SET received_at = started_at,
                processed_at = completed_at,
                error_summary = error_message,
                status = CASE WHEN status = 'success' THEN 'processed' ELSE status END
            """
        )
    )

    with op.batch_alter_table("ingestion_batches") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=100),
            existing_nullable=False,
            server_default="received",
        )
        batch_op.alter_column(
            "received_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        batch_op.drop_column("rejected_count")
        batch_op.drop_column("accepted_count")
        batch_op.drop_column("error_message")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
