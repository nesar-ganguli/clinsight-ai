from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    fhir_observation_id = Column(String, nullable=True)
    observation_code = Column(String, nullable=True)
    observation_name = Column(String, nullable=True)
    value = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    effective_date = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="observations")
