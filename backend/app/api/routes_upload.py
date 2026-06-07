import json
import hashlib
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.audit import write_audit_event
from app.services.auth import require_roles
from app.services.ingestion import ingest_fhir_bundle

router = APIRouter()


@router.post("/upload")
async def upload_fhir_bundle(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "data_reviewer")),
):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    try:
        content = await file.read()
        bundle = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Could not decode file as UTF-8")

    if bundle.get("resourceType") != "Bundle" or bundle.get("type") != "collection":
        raise HTTPException(status_code=400, detail="Uploaded JSON is not a FHIR Bundle")

    try:
        content_hash = hashlib.sha256(content).hexdigest()
        result = ingest_fhir_bundle(bundle, db, filename=file.filename, content_hash=content_hash)
        write_audit_event(
            db,
            user=user,
            action="fhir_bundle_uploaded",
            resource_type="patient",
            resource_id=str(result["patient_id"]),
            metadata={
                "filename": file.filename,
                "content_hash": content_hash,
                "patient_id": result["patient_id"],
                "import_mode": result["import_mode"],
                "resource_counts": result["resource_counts"],
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message": "FHIR bundle parsed and stored successfully",
        **result,
    }
