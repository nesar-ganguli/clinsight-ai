from fastapi import FastAPI
from app.api.routes_upload import router as upload_router
from app.api.routes_patient import router as patient_router
from app.api.routes_quality import router as quality_router
from app.core.database import Base, engine

from app.models.patient import Patient
from app.models.condition import Condition
from app.models.observation import Observation

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ClinSight AI Backend",
    description="AI Clinical Data Interpreter backend",
    version="0.1.0"
)

app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(patient_router, prefix="/api", tags=["Patients"])
app.include_router(quality_router, prefix="/api", tags=["Quality"])


@app.get("/")
def root():
    return {"message": "ClinSight AI backend is running"}
