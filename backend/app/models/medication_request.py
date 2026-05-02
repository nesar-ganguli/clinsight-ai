from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class MedicationRequest(Base):
    __tablename__ = "medication_requests"
    __table_args__ = (
        UniqueConstraint(
            "patient_id",
            "fhir_medication_request_id",
            name="uq_medication_requests_patient_fhir_medication_request_id"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    fhir_medication_request_id = Column(String(255), nullable=True)
    status = Column(String(100), nullable=True)
    intent = Column(String(100), nullable=True)
    medication_code = Column(String(100), nullable=True, index=True)
    medication_name = Column(String(255), nullable=True)
    authored_on = Column(String(64), nullable=True)
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

    patient = relationship("Patient", back_populates="medication_requests")
