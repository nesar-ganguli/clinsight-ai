from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class CuratedRecordSource(Base):
    __tablename__ = "curated_record_sources"

    id = Column(Integer, primary_key=True, index=True)
    curated_table_name = Column(String(100), nullable=False, index=True)
    curated_record_id = Column(Integer, nullable=False, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_table_name = Column(String(100), nullable=True)
    raw_record_id = Column(String(255), nullable=True)
    transform_version = Column(String(100), nullable=False, default="fhir-upload-v1", server_default="fhir-upload-v1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_system = relationship("SourceSystem")
    ingestion_batch = relationship("IngestionBatch")
