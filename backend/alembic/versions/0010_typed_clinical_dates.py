"""Convert curated clinical date strings to timezone-aware timestamps.

Revision ID: 0010_typed_clinical_dates
Revises: 0009_canonical_patient_identity
Create Date: 2026-08-25 00:00:00
"""

import re
from datetime import date, datetime, time, timezone
from typing import Any, Optional

import sqlalchemy as sa
from alembic import op


revision = "0010_typed_clinical_dates"
down_revision = "0009_canonical_patient_identity"
branch_labels = None
depends_on = None


CLINICAL_DATETIME_COLUMNS = {
    "conditions": ("onset_date",),
    "observations": ("effective_date",),
    "encounters": ("period_start", "period_end"),
    "medication_requests": ("authored_on",),
    "allergy_intolerances": ("recorded_date",),
}
DATE_ONLY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TEMP_PREFIX = "_typed_"


def upgrade() -> None:
    for table_name, column_names in CLINICAL_DATETIME_COLUMNS.items():
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                batch_op.add_column(
                    sa.Column(
                        _temporary_column_name(column_name),
                        sa.DateTime(timezone=True),
                        nullable=True,
                    )
                )

        for column_name in column_names:
            _copy_text_to_datetime(table_name, column_name)

        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                batch_op.drop_column(column_name)
                batch_op.alter_column(
                    _temporary_column_name(column_name),
                    new_column_name=column_name,
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=True,
                )


def downgrade() -> None:
    for table_name, column_names in reversed(tuple(CLINICAL_DATETIME_COLUMNS.items())):
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                batch_op.add_column(
                    sa.Column(
                        _temporary_column_name(column_name),
                        sa.String(length=64),
                        nullable=True,
                    )
                )

        for column_name in column_names:
            _copy_datetime_to_text(table_name, column_name)

        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                batch_op.drop_column(column_name)
                batch_op.alter_column(
                    _temporary_column_name(column_name),
                    new_column_name=column_name,
                    existing_type=sa.String(length=64),
                    existing_nullable=True,
                )


def _copy_text_to_datetime(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    source_table = sa.table(
        table_name,
        sa.column("id", sa.Integer()),
        sa.column(column_name, sa.String(length=64)),
    )
    values = []
    for record_id, raw_value in bind.execute(
        sa.select(source_table.c.id, source_table.c[column_name])
    ):
        parsed_value = _parse_datetime(raw_value)
        if parsed_value is not None:
            values.append({"record_id": record_id, "typed_value": parsed_value})

    if not values:
        return

    target_column_name = _temporary_column_name(column_name)
    target_table = sa.table(
        table_name,
        sa.column("id", sa.Integer()),
        sa.column(target_column_name, sa.DateTime(timezone=True)),
    )
    statement = (
        target_table.update()
        .where(target_table.c.id == sa.bindparam("record_id"))
        .values(
            {
                target_column_name: sa.bindparam(
                    "typed_value",
                    type_=sa.DateTime(timezone=True),
                )
            }
        )
    )
    bind.execute(statement, values)


def _copy_datetime_to_text(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    source_table = sa.table(
        table_name,
        sa.column("id", sa.Integer()),
        sa.column(column_name, sa.DateTime(timezone=True)),
    )
    values = []
    for record_id, raw_value in bind.execute(
        sa.select(source_table.c.id, source_table.c[column_name])
    ):
        serialized_value = _format_datetime(raw_value)
        if serialized_value is not None:
            values.append({"record_id": record_id, "text_value": serialized_value})

    if not values:
        return

    target_column_name = _temporary_column_name(column_name)
    target_table = sa.table(
        table_name,
        sa.column("id", sa.Integer()),
        sa.column(target_column_name, sa.String(length=64)),
    )
    statement = (
        target_table.update()
        .where(target_table.c.id == sa.bindparam("record_id"))
        .values({target_column_name: sa.bindparam("text_value", type_=sa.String(length=64))})
    )
    bind.execute(statement, values)


def _temporary_column_name(column_name: str) -> str:
    return f"{TEMP_PREFIX}{column_name}"


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            if DATE_ONLY_PATTERN.fullmatch(normalized):
                parsed = datetime.combine(date.fromisoformat(normalized), time.min)
            else:
                if normalized.endswith(("Z", "z")):
                    normalized = f"{normalized[:-1]}+00:00"
                parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_datetime(value: Any) -> Optional[str]:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return parsed.isoformat().replace("+00:00", "Z")
