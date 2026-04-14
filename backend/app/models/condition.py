from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class Condition(Base):
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    fhir_condition_id = Column(String, nullable=True)
    condition_code = Column(String, nullable=True)
    condition_name = Column(String, nullable=True)
    clinical_status = Column(String, nullable=True)
    onset_date = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="conditions")
