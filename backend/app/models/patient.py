from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    fhir_patient_id = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    birth_date = Column(String, nullable=True)

    conditions = relationship("Condition", back_populates="patient", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="patient", cascade="all, delete-orphan")
