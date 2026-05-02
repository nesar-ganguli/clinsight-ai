from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class StagingPatientIdentity(Base):
    __tablename__ = "staging_patient_identities"

    id = Column(Integer, primary_key=True, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_table_name = Column(String(100), nullable=True)
    raw_record_id = Column(String(255), nullable=True)
    source_patient_id = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    birth_date = Column(String(32), nullable=True)
    candidate_patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True)
    match_status = Column(String(100), nullable=False, default="pending", server_default="pending")
    match_confidence = Column(Float, nullable=True)
    match_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    source_system = relationship("SourceSystem")
    ingestion_batch = relationship("IngestionBatch")
    candidate_patient = relationship("Patient")


class StagingClinicalResource(Base):
    __tablename__ = "staging_clinical_resources"

    id = Column(Integer, primary_key=True, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_table_name = Column(String(100), nullable=True)
    raw_record_id = Column(String(255), nullable=True)
    source_patient_id = Column(String(255), nullable=True, index=True)
    target_resource_type = Column(String(100), nullable=False, index=True)
    normalized_payload = Column(JSON, nullable=True)
    validation_status = Column(String(100), nullable=False, default="pending", server_default="pending")
    validation_errors = Column(JSON, nullable=True)
    curated_table_name = Column(String(100), nullable=True)
    curated_record_id = Column(Integer, nullable=True, index=True)
    transform_version = Column(String(100), nullable=False, default="v1", server_default="v1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    source_system = relationship("SourceSystem")
    ingestion_batch = relationship("IngestionBatch")
