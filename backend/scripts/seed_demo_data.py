import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.allergy_intolerance import AllergyIntolerance
from app.models.condition import Condition
from app.models.encounter import Encounter
from app.models.medication_request import MedicationRequest
from app.models.observation import Observation
from app.models.patient import Patient
from app.services.ingestion import ingest_fhir_bundle


SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def reset_database(db):
    db.query(AllergyIntolerance).delete()
    db.query(Condition).delete()
    db.query(Encounter).delete()
    db.query(MedicationRequest).delete()
    db.query(Observation).delete()
    db.query(Patient).delete()
    db.commit()


def load_bundle(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    db = SessionLocal()
    try:
        if os.getenv("RESET_DEMO_DATA", "true").lower() == "true":
            reset_database(db)

        results = []
        for bundle_path in sorted(SAMPLE_DATA_DIR.glob("patient_bundle_*.json")):
            result = ingest_fhir_bundle(load_bundle(bundle_path), db)
            results.append((bundle_path.name, result))

        print("Seeded ClinSight demo data")
        for filename, result in results:
            print(
                f"- {filename}: patient #{result['patient_id']} "
                f"({result['import_mode']}), resources={result['resource_counts']}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
