from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PatientSourceIdentifier(Base):
    __tablename__ = "patient_source_identifiers"
    __table_args__ = (
        UniqueConstraint(
            "source_system_id",
            "identifier_value",
            name="uq_patient_source_identifiers_source_value"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    identifier_type = Column(String(100), nullable=False)
    identifier_value = Column(String(255), nullable=False)
    assigning_authority = Column(String(255), nullable=True)
    last_seen_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    patient = relationship("Patient", back_populates="source_identifiers")
    source_system = relationship("SourceSystem", back_populates="patient_identifiers")
    last_seen_batch = relationship("IngestionBatch")
