from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RawHospitalPatient(Base):
    __tablename__ = "raw_hospital_patients"
    __table_args__ = (
        UniqueConstraint("source_system_id", "source_record_id", name="uq_raw_hospital_patients_source_record"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    source_record_id = Column(String(255), nullable=True, index=True)
    source_patient_id = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    full_name = Column(String(255), nullable=True, index=True)
    gender = Column(String(50), nullable=True)
    birth_date = Column(String(32), nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    row_hash = Column(String(64), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_system = relationship("SourceSystem")
    ingestion_batch = relationship("IngestionBatch")


class RawHospitalEncounter(Base):
    __tablename__ = "raw_hospital_encounters"
    __table_args__ = (
        UniqueConstraint("source_system_id", "source_encounter_id", name="uq_raw_hospital_encounters_source_encounter"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    source_encounter_id = Column(String(255), nullable=True, index=True)
    source_patient_id = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    encounter_status = Column(String(100), nullable=True)
    encounter_class = Column(String(100), nullable=True)
    encounter_type = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    admit_datetime = Column(String(64), nullable=True)
    discharge_datetime = Column(String(64), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    row_hash = Column(String(64), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_system = relationship("SourceSystem")
    ingestion_batch = relationship("IngestionBatch")


class RawHospitalDiagnosis(Base):
    __tablename__ = "raw_hospital_diagnoses"
    __table_args__ = (
        UniqueConstraint("source_system_id", "source_diagnosis_id", name="uq_raw_hospital_diagnoses_source_diagnosis"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    source_diagnosis_id = Column(String(255), nullable=True, index=True)
    source_patient_id = Column(String(255), nullable=True, index=True)
    source_encounter_id = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    diagnosis_type = Column(String(100), nullable=True)
    code_system = Column(String(100), nullable=True)
    diagnosis_code = Column(String(100), nullable=True, index=True)
    diagnosis_description = Column(String(255), nullable=True)
    clinical_status = Column(String(100), nullable=True)
    onset_date = Column(String(64), nullable=True)
    resolution_date = Column(String(64), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    row_hash = Column(String(64), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_system = relationship("SourceSystem")
    ingestion_batch = relationship("IngestionBatch")


class RawHospitalObservation(Base):
    __tablename__ = "raw_hospital_observations"
    __table_args__ = (
        UniqueConstraint("source_system_id", "source_observation_id", name="uq_raw_hospital_observations_source_observation"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    source_observation_id = Column(String(255), nullable=True, index=True)
    source_patient_id = Column(String(255), nullable=True, index=True)
    source_encounter_id = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    observation_type = Column(String(100), nullable=True)
    code_system = Column(String(100), nullable=True)
    observation_code = Column(String(100), nullable=True, index=True)
    observation_name = Column(String(255), nullable=True)
    value = Column(String(255), nullable=True)
    unit = Column(String(64), nullable=True)
    observed_at = Column(String(64), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    row_hash = Column(String(64), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_system = relationship("SourceSystem")
    ingestion_batch = relationship("IngestionBatch")


class RawHospitalMedication(Base):
    __tablename__ = "raw_hospital_medications"
    __table_args__ = (
        UniqueConstraint("source_system_id", "source_medication_id", name="uq_raw_hospital_medications_source_medication"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    source_medication_id = Column(String(255), nullable=True, index=True)
    source_patient_id = Column(String(255), nullable=True, index=True)
    source_encounter_id = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    medication_code = Column(String(100), nullable=True, index=True)
    medication_name = Column(String(255), nullable=True)
    status = Column(String(100), nullable=True)
    start_date = Column(String(64), nullable=True)
    end_date = Column(String(64), nullable=True)
    authored_on = Column(String(64), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    row_hash = Column(String(64), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_system = relationship("SourceSystem")
    ingestion_batch = relationship("IngestionBatch")


class RawHospitalAllergy(Base):
    __tablename__ = "raw_hospital_allergies"
    __table_args__ = (
        UniqueConstraint("source_system_id", "source_allergy_id", name="uq_raw_hospital_allergies_source_allergy"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system_id = Column(Integer, ForeignKey("source_systems.id"), nullable=False, index=True)
    ingestion_batch_id = Column(Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    source_allergy_id = Column(String(255), nullable=True, index=True)
    source_patient_id = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    allergen_code = Column(String(100), nullable=True, index=True)
    allergen_name = Column(String(255), nullable=True)
    reaction = Column(String(255), nullable=True)
    severity = Column(String(100), nullable=True)
    criticality = Column(String(100), nullable=True)
    verification_status = Column(String(100), nullable=True)
    clinical_status = Column(String(100), nullable=True)
    recorded_date = Column(String(64), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    row_hash = Column(String(64), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_system = relationship("SourceSystem")
    ingestion_batch = relationship("IngestionBatch")
