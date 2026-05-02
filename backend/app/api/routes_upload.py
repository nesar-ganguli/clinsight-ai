import json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ingestion import ingest_fhir_bundle

router = APIRouter()


@router.post("/upload")
async def upload_fhir_bundle(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    try:
        content = await file.read()
        bundle = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Could not decode file as UTF-8")

    if bundle.get("resourceType") != "Bundle":
        raise HTTPException(status_code=400, detail="Uploaded JSON is not a FHIR Bundle")

    try:
        result = ingest_fhir_bundle(bundle, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message": "FHIR bundle parsed and stored successfully",
        **result,
    }
