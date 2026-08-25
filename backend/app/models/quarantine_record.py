from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class QuarantineRecord(Base):
    __tablename__ = "quarantine_records"

    id = Column(Integer, primary_key=True, index=True)
    ingestion_batch_id = Column(
        Integer,
        ForeignKey("ingestion_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_system_id = Column(
        Integer,
        ForeignKey("source_systems.id"),
        nullable=False,
        index=True,
    )
    resource_type = Column(String(100), nullable=False, index=True)
    source_record_id = Column(String(255), nullable=True, index=True)
    error_code = Column(String(100), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    raw_payload = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ingestion_batch = relationship("IngestionBatch")
    source_system = relationship("SourceSystem")
