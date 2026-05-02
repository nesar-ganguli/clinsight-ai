from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint, func, true
from sqlalchemy.orm import relationship

from app.core.database import Base


class SourceSystem(Base):
    __tablename__ = "source_systems"
    __table_args__ = (
        UniqueConstraint("name", name="uq_source_systems_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    system_type = Column(String(100), nullable=False)
    facility_name = Column(String(255), nullable=True)
    external_system_id = Column(String(255), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    ingestion_batches = relationship("IngestionBatch", back_populates="source_system")
    patient_identifiers = relationship("PatientSourceIdentifier", back_populates="source_system")
