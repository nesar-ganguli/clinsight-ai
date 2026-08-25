"""Add quarantine records for invalid child resources.

Revision ID: 0012_quarantine_records
Revises: 0011_durable_batch_states
Create Date: 2026-08-25 00:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision = "0012_quarantine_records"
down_revision = "0011_durable_batch_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quarantine_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingestion_batch_id", sa.Integer(), nullable=False),
        sa.Column("source_system_id", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column(
            "raw_payload",
            sa.JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_batch_id"],
            ["ingestion_batches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["source_system_id"], ["source_systems.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quarantine_records_id"), "quarantine_records", ["id"])
    op.create_index(
        op.f("ix_quarantine_records_ingestion_batch_id"),
        "quarantine_records",
        ["ingestion_batch_id"],
    )
    op.create_index(
        op.f("ix_quarantine_records_source_system_id"),
        "quarantine_records",
        ["source_system_id"],
    )
    op.create_index(
        op.f("ix_quarantine_records_resource_type"),
        "quarantine_records",
        ["resource_type"],
    )
    op.create_index(
        op.f("ix_quarantine_records_source_record_id"),
        "quarantine_records",
        ["source_record_id"],
    )
    op.create_index(
        op.f("ix_quarantine_records_error_code"),
        "quarantine_records",
        ["error_code"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_quarantine_records_error_code"), table_name="quarantine_records")
    op.drop_index(op.f("ix_quarantine_records_source_record_id"), table_name="quarantine_records")
    op.drop_index(op.f("ix_quarantine_records_resource_type"), table_name="quarantine_records")
    op.drop_index(op.f("ix_quarantine_records_source_system_id"), table_name="quarantine_records")
    op.drop_index(op.f("ix_quarantine_records_ingestion_batch_id"), table_name="quarantine_records")
    op.drop_index(op.f("ix_quarantine_records_id"), table_name="quarantine_records")
    op.drop_table("quarantine_records")
