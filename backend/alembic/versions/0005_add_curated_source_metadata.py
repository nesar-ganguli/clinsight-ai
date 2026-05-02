"""Add source metadata to curated clinical tables

Revision ID: 0005_curated_source_metadata
Revises: 0004_raw_operational
Create Date: 2026-05-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_curated_source_metadata"
down_revision = "0004_raw_operational"
branch_labels = None
depends_on = None


CURATED_TABLES = [
    "patients",
    "conditions",
    "observations",
    "encounters",
    "medication_requests",
    "allergy_intolerances",
]


def upgrade() -> None:
    for table_name in CURATED_TABLES:
        op.add_column(table_name, sa.Column("source_type", sa.String(length=100), nullable=True))
        op.add_column(table_name, sa.Column("source_system", sa.String(length=255), nullable=True))
        op.add_column(table_name, sa.Column("source_record_id", sa.String(length=255), nullable=True))
        op.add_column(table_name, sa.Column("ingestion_batch_id", sa.String(length=255), nullable=True))
        op.add_column(table_name, sa.Column("transformed_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index(op.f(f"ix_{table_name}_source_type"), table_name, ["source_type"], unique=False)
        op.create_index(op.f(f"ix_{table_name}_source_record_id"), table_name, ["source_record_id"], unique=False)
        op.create_index(op.f(f"ix_{table_name}_ingestion_batch_id"), table_name, ["ingestion_batch_id"], unique=False)


def downgrade() -> None:
    for table_name in reversed(CURATED_TABLES):
        op.drop_index(op.f(f"ix_{table_name}_ingestion_batch_id"), table_name=table_name)
        op.drop_index(op.f(f"ix_{table_name}_source_record_id"), table_name=table_name)
        op.drop_index(op.f(f"ix_{table_name}_source_type"), table_name=table_name)
        op.drop_column(table_name, "transformed_at")
        op.drop_column(table_name, "ingestion_batch_id")
        op.drop_column(table_name, "source_record_id")
        op.drop_column(table_name, "source_system")
        op.drop_column(table_name, "source_type")
