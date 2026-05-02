from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id = Column(Integer, primary_key=True, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_type = Column(String(100), nullable=False, index=True)
    filename = Column(String(255), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    status = Column(String(100), nullable=False, default="received", server_default="received")
    record_count = Column(Integer, nullable=False, default=0, server_default="0")
    error_summary = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    source_system = relationship("SourceSystem", back_populates="ingestion_batches")
