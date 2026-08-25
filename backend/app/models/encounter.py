from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Encounter(Base):
    __tablename__ = "encounters"
    __table_args__ = (
        UniqueConstraint(
            "patient_id",
            "source_system",
            "fhir_encounter_id",
            name="uq_encounters_patient_source_fhir_encounter_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    fhir_encounter_id = Column(String(255), nullable=True)
    status = Column(String(100), nullable=True)
    encounter_class = Column(String(100), nullable=True)
    encounter_type = Column(String(255), nullable=True)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    source_type = Column(String(100), nullable=True, index=True)
    source_system = Column(String(255), nullable=True)
    source_record_id = Column(String(255), nullable=True, index=True)
    ingestion_batch_id = Column(String(255), nullable=True, index=True)
    transformed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    patient = relationship("Patient", back_populates="encounters")
