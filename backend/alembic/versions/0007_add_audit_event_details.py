"""Add detailed audit event fields

Revision ID: 0007_audit_event_details
Revises: 0006_auth_rbac_audit
Create Date: 2026-05-03 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_audit_event_details"
down_revision = "0006_auth_rbac_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("resource_type", sa.String(length=100), nullable=True))
    op.add_column("audit_logs", sa.Column("resource_id", sa.String(length=255), nullable=True))
    op.add_column(
        "audit_logs",
        sa.Column("event_timestamp", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.add_column("audit_logs", sa.Column("metadata", sa.JSON(), nullable=True))
    op.create_index(op.f("ix_audit_logs_resource_type"), "audit_logs", ["resource_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_resource_id"), "audit_logs", ["resource_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_event_timestamp"), "audit_logs", ["event_timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_event_timestamp"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource_type"), table_name="audit_logs")
    op.drop_column("audit_logs", "metadata")
    op.drop_column("audit_logs", "event_timestamp")
    op.drop_column("audit_logs", "resource_id")
    op.drop_column("audit_logs", "resource_type")
