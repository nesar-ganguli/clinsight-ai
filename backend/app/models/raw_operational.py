from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint, func

from app.core.database import Base


class RawPatient(Base):
    __tablename__ = "raw_patients"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_patients_source_record_batch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(255), nullable=False, index=True)
    source_record_id = Column(String(255), nullable=False, index=True)
    ingestion_batch_id = Column(String(255), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    mrn = Column(String(255), nullable=True, index=True)
    enterprise_patient_id = Column(String(255), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True, index=True)
    date_of_birth = Column(String(32), nullable=True)
    sex = Column(String(50), nullable=True)
    address_line = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    postal_code = Column(String(20), nullable=True)
    phone = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)


class RawEncounter(Base):
    __tablename__ = "raw_encounters"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_encounters_source_record_batch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(255), nullable=False, index=True)
    source_record_id = Column(String(255), nullable=False, index=True)
    ingestion_batch_id = Column(String(255), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    encounter_number = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    department_code = Column(String(100), nullable=True, index=True)
    attending_provider_id = Column(String(255), nullable=True, index=True)
    encounter_type = Column(String(100), nullable=True)
    admit_datetime = Column(String(64), nullable=True)
    discharge_datetime = Column(String(64), nullable=True)
    discharge_disposition = Column(String(255), nullable=True)
    financial_class = Column(String(100), nullable=True)


class RawDiagnosis(Base):
    __tablename__ = "raw_diagnoses"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_diagnoses_source_record_batch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(255), nullable=False, index=True)
    source_record_id = Column(String(255), nullable=False, index=True)
    ingestion_batch_id = Column(String(255), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    encounter_number = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    diagnosis_code = Column(String(100), nullable=True, index=True)
    diagnosis_description = Column(String(255), nullable=True)
    code_system = Column(String(100), nullable=True)
    diagnosis_type = Column(String(100), nullable=True)
    present_on_admission = Column(String(20), nullable=True)
    diagnosis_datetime = Column(String(64), nullable=True)
    ranking = Column(Integer, nullable=True)


class RawLab(Base):
    __tablename__ = "raw_labs"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_labs_source_record_batch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(255), nullable=False, index=True)
    source_record_id = Column(String(255), nullable=False, index=True)
    ingestion_batch_id = Column(String(255), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    order_id = Column(String(255), nullable=True, index=True)
    encounter_number = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    lab_code = Column(String(100), nullable=True, index=True)
    lab_name = Column(String(255), nullable=True)
    result_value = Column(String(255), nullable=True)
    result_numeric = Column(Float, nullable=True)
    result_unit = Column(String(64), nullable=True)
    reference_range = Column(String(100), nullable=True)
    abnormal_flag = Column(String(50), nullable=True)
    result_status = Column(String(100), nullable=True)
    collected_at = Column(String(64), nullable=True)
    resulted_at = Column(String(64), nullable=True)


class RawMedication(Base):
    __tablename__ = "raw_medications"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_medications_source_record_batch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(255), nullable=False, index=True)
    source_record_id = Column(String(255), nullable=False, index=True)
    ingestion_batch_id = Column(String(255), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    order_id = Column(String(255), nullable=True, index=True)
    encounter_number = Column(String(255), nullable=True, index=True)
    mrn = Column(String(255), nullable=True, index=True)
    medication_code = Column(String(100), nullable=True, index=True)
    medication_name = Column(String(255), nullable=True)
    dose = Column(String(100), nullable=True)
    route = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    order_status = Column(String(100), nullable=True)
    ordered_at = Column(String(64), nullable=True)
    start_datetime = Column(String(64), nullable=True)
    stop_datetime = Column(String(64), nullable=True)
    ordering_provider_id = Column(String(255), nullable=True, index=True)


class RawAllergy(Base):
    __tablename__ = "raw_allergies"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_allergies_source_record_batch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(255), nullable=False, index=True)
    source_record_id = Column(String(255), nullable=False, index=True)
    ingestion_batch_id = Column(String(255), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    mrn = Column(String(255), nullable=True, index=True)
    allergen_code = Column(String(100), nullable=True, index=True)
    allergen_name = Column(String(255), nullable=True)
    allergen_type = Column(String(100), nullable=True)
    reaction = Column(String(255), nullable=True)
    severity = Column(String(100), nullable=True)
    allergy_status = Column(String(100), nullable=True)
    recorded_at = Column(String(64), nullable=True)


class RawProvider(Base):
    __tablename__ = "raw_providers"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_providers_source_record_batch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(255), nullable=False, index=True)
    source_record_id = Column(String(255), nullable=False, index=True)
    ingestion_batch_id = Column(String(255), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    provider_id = Column(String(255), nullable=True, index=True)
    npi = Column(String(50), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True, index=True)
    credentials = Column(String(100), nullable=True)
    specialty = Column(String(255), nullable=True)
    department_code = Column(String(100), nullable=True, index=True)
    employment_status = Column(String(100), nullable=True)


class RawDepartment(Base):
    __tablename__ = "raw_departments"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", "ingestion_batch_id", name="uq_raw_departments_source_record_batch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(255), nullable=False, index=True)
    source_record_id = Column(String(255), nullable=False, index=True)
    ingestion_batch_id = Column(String(255), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    department_code = Column(String(100), nullable=True, index=True)
    department_name = Column(String(255), nullable=True)
    facility_code = Column(String(100), nullable=True, index=True)
    facility_name = Column(String(255), nullable=True)
    service_line = Column(String(255), nullable=True)
    location_type = Column(String(100), nullable=True)
    active_flag = Column(String(20), nullable=True)
