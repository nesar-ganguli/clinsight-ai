from sqlalchemy import inspect

from app.core.database import SessionLocal, engine
from app.models.raw_operational import RawLab, RawPatient
from scripts.generate_hospital_data import generate_patients


def test_raw_operational_tables_are_created():
    inspector = inspect(engine)

    assert {
        "raw_patients",
        "raw_encounters",
        "raw_diagnoses",
        "raw_labs",
        "raw_medications",
        "raw_allergies",
        "raw_providers",
        "raw_departments",
    }.issubset(set(inspector.get_table_names()))


def test_raw_patient_can_be_inserted_without_curated_patient():
    db = SessionLocal()
    try:
        raw_patient = RawPatient(
            source_system="epic_clarity",
            source_record_id="PAT-10001",
            ingestion_batch_id="batch-20260502-001",
            mrn="MRN123456",
            enterprise_patient_id="EPI987654",
            first_name="Avery",
            last_name="Morgan",
            date_of_birth="1978-04-12",
            sex="female",
            city="Indianapolis",
            state="IN",
        )

        db.add(raw_patient)
        db.commit()

        assert raw_patient.id is not None
        assert db.query(RawPatient).count() == 1
    finally:
        db.close()


def test_synthetic_generator_builds_controlled_raw_records_only():
    records, counts = generate_patients(
        patient_count=60,
        seed=42,
        source_system="test_hospital_ods",
        batch_id="test-batch-raw-only",
    )

    assert counts["raw_patients"] == 60
    assert counts["raw_encounters"] >= 60
    assert counts["raw_diagnoses"] > 0
    assert counts["raw_labs"] > 0
    assert counts["raw_medications"] > 0
    assert counts["raw_providers"] > 0
    assert counts["raw_departments"] > 0
    assert all(record.__tablename__.startswith("raw_") for record in records)

    labs = [record for record in records if isinstance(record, RawLab)]
    assert any(lab.lab_code == "4548-4" for lab in labs)
    assert any(lab.lab_code in {"BP-SYS", "BP-DIA"} for lab in labs)
    assert any("CONFLICT" in lab.source_record_id for lab in labs)
