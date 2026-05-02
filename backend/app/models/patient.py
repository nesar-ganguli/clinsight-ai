from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    fhir_patient_id = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True, index=True)
    gender = Column(String(50), nullable=True)
    birth_date = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    conditions = relationship("Condition", back_populates="patient", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="patient", cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    medication_requests = relationship("MedicationRequest", back_populates="patient", cascade="all, delete-orphan")
    allergies = relationship("AllergyIntolerance", back_populates="patient", cascade="all, delete-orphan")
    source_identifiers = relationship("PatientSourceIdentifier", back_populates="patient", cascade="all, delete-orphan")
