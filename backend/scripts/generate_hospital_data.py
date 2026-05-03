import argparse
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.raw_operational import (
    RawAllergy,
    RawDepartment,
    RawDiagnosis,
    RawEncounter,
    RawLab,
    RawMedication,
    RawPatient,
    RawProvider,
)
from app.services.audit import write_audit_event


DEFAULT_SOURCE_SYSTEM = "internal_hospital_ods"
ANCHOR_DATE = date(2026, 5, 2)
INGESTED_AT = datetime(2026, 5, 2, 0, 0, tzinfo=timezone.utc)

FIRST_NAMES = [
    "Avery",
    "Jordan",
    "Taylor",
    "Morgan",
    "Casey",
    "Riley",
    "Cameron",
    "Quinn",
    "Parker",
    "Reese",
    "Maya",
    "Elena",
    "Nora",
    "Sofia",
    "Liam",
    "Noah",
    "Ethan",
    "Amir",
    "Mateo",
    "Lucas",
]
LAST_NAMES = [
    "Morgan",
    "Rivera",
    "Patel",
    "Chen",
    "Johnson",
    "Williams",
    "Brown",
    "Garcia",
    "Miller",
    "Davis",
    "Singh",
    "Nguyen",
    "Khan",
    "Thompson",
    "Wilson",
    "Anderson",
]
STREETS = ["Maple", "Oak", "Cedar", "Washington", "Market", "College", "Meridian", "Main"]
INDIANA_CITIES = ["Indianapolis", "Carmel", "Fishers", "Noblesville", "Greenwood", "Plainfield"]

DEPARTMENTS = [
    ("CARD", "Cardiology", "Heart and Vascular", "Clinic"),
    ("ENDO", "Endocrinology", "Medicine", "Clinic"),
    ("FMED", "Family Medicine", "Primary Care", "Clinic"),
    ("ED", "Emergency Department", "Emergency Medicine", "Emergency"),
    ("LAB", "Clinical Laboratory", "Diagnostics", "Ancillary"),
    ("NEPH", "Nephrology", "Medicine", "Clinic"),
]

PROVIDER_SPECIALTIES = [
    ("Family Medicine", "FMED"),
    ("Internal Medicine", "FMED"),
    ("Endocrinology", "ENDO"),
    ("Cardiology", "CARD"),
    ("Emergency Medicine", "ED"),
    ("Nephrology", "NEPH"),
]

DIAGNOSES = {
    "diabetes": ("E11.9", "Type 2 diabetes mellitus without complications", "ICD-10-CM"),
    "hypertension": ("I10", "Essential hypertension", "ICD-10-CM"),
    "hyperlipidemia": ("E78.5", "Hyperlipidemia, unspecified", "ICD-10-CM"),
    "ckd": ("N18.30", "Chronic kidney disease, stage 3 unspecified", "ICD-10-CM"),
    "asthma": ("J45.909", "Unspecified asthma, uncomplicated", "ICD-10-CM"),
}

MEDICATIONS = {
    "diabetes": [
        ("RXN-860975", "Metformin 500 MG Oral Tablet", "500 mg", "oral", "twice daily"),
        ("RXN-311041", "Insulin glargine 100 UNT/ML Injectable Solution", "10 units", "subcutaneous", "nightly"),
    ],
    "hypertension": [
        ("RXN-29046", "Lisinopril 10 MG Oral Tablet", "10 mg", "oral", "daily"),
        ("RXN-197361", "Amlodipine 5 MG Oral Tablet", "5 mg", "oral", "daily"),
    ],
    "hyperlipidemia": [
        ("RXN-617314", "Atorvastatin 20 MG Oral Tablet", "20 mg", "oral", "nightly"),
    ],
    "asthma": [
        ("RXN-745679", "Albuterol 0.09 MG/ACTUAT Metered Dose Inhaler", "2 puffs", "inhalation", "as needed"),
    ],
}

ALLERGIES = [
    ("7980", "Penicillin", "drug", "rash", "moderate"),
    ("2670", "Codeine", "drug", "nausea", "mild"),
    ("227493005", "Cashew nut", "food", "hives", "moderate"),
    ("91936005", "Latex", "environmental", "contact dermatitis", "mild"),
]


@dataclass(frozen=True)
class PatientProfile:
    index: int
    mrn: str
    encounter_numbers: list[str]
    conditions: set[str]
    has_a1c: bool
    has_bp: bool
    conflicting_labs: bool
    missing_active_medication: bool


def build_departments(source_system: str, batch_id: str) -> list[RawDepartment]:
    records = []
    for index, (code, name, service_line, location_type) in enumerate(DEPARTMENTS, start=1):
        records.append(
            RawDepartment(
                source_system=source_system,
                source_record_id=f"DEPT-{code}",
                ingestion_batch_id=batch_id,
                ingested_at=INGESTED_AT,
                department_code=code,
                department_name=name,
                facility_code="CLINMAIN",
                facility_name="ClinSight Memorial Hospital",
                service_line=service_line,
                location_type=location_type,
                active_flag="Y",
            )
        )
    return records


def build_providers(rng: random.Random, source_system: str, batch_id: str, count: int = 36) -> list[RawProvider]:
    providers = []
    for index in range(1, count + 1):
        specialty, department_code = PROVIDER_SPECIALTIES[(index - 1) % len(PROVIDER_SPECIALTIES)]
        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)
        provider_id = f"PROV{index:04d}"
        providers.append(
            RawProvider(
                source_system=source_system,
                source_record_id=provider_id,
                ingestion_batch_id=batch_id,
                ingested_at=INGESTED_AT,
                provider_id=provider_id,
                npi=f"19{rng.randint(10000000, 99999999)}",
                first_name=first_name,
                last_name=last_name,
                credentials=rng.choice(["MD", "DO", "NP", "PA"]),
                specialty=specialty,
                department_code=department_code,
                employment_status="active",
            )
        )
    return providers


def build_patient_profile(index: int, rng: random.Random) -> PatientProfile:
    conditions: set[str] = set()
    conflicting_labs = index % 50 == 0
    if conflicting_labs:
        conditions.add("diabetes")
    if index % 3 == 0 or rng.random() < 0.18:
        conditions.add("diabetes")
    if index % 4 == 0 or rng.random() < 0.24:
        conditions.add("hypertension")
    if rng.random() < 0.22:
        conditions.add("hyperlipidemia")
    if rng.random() < 0.08:
        conditions.add("ckd")
    if rng.random() < 0.07:
        conditions.add("asthma")
    if not conditions and rng.random() < 0.35:
        conditions.add(rng.choice(["hypertension", "hyperlipidemia", "asthma"]))

    encounter_count = rng.randint(1, 4)
    mrn = f"MRN{index:07d}"
    encounter_numbers = [f"ENC{index:07d}-{enc_index}" for enc_index in range(1, encounter_count + 1)]
    return PatientProfile(
        index=index,
        mrn=mrn,
        encounter_numbers=encounter_numbers,
        conditions=conditions,
        has_a1c=conflicting_labs or index % 10 not in {0, 1},
        has_bp=index % 8 not in {0, 1},
        conflicting_labs=conflicting_labs,
        missing_active_medication=index % 12 == 0,
    )


def generate_patients(
    patient_count: int,
    seed: int,
    source_system: str,
    batch_id: str,
) -> tuple[list[object], dict[str, int]]:
    rng = random.Random(seed)
    records: list[object] = []
    providers = build_providers(rng, source_system, batch_id)
    provider_ids = [provider.provider_id for provider in providers if provider.provider_id]
    department_codes = [department[0] for department in DEPARTMENTS]
    records.extend(build_departments(source_system, batch_id))
    records.extend(providers)

    counts = {
        "raw_patients": 0,
        "raw_encounters": 0,
        "raw_diagnoses": 0,
        "raw_labs": 0,
        "raw_medications": 0,
        "raw_allergies": 0,
        "raw_providers": len(providers),
        "raw_departments": len(DEPARTMENTS),
    }

    start_date = ANCHOR_DATE - timedelta(days=720)
    for index in range(1, patient_count + 1):
        profile = build_patient_profile(index, rng)
        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)
        birth_date = random_birth_date(rng)

        records.append(
            RawPatient(
                source_system=source_system,
                source_record_id=f"PAT{index:07d}",
                ingestion_batch_id=batch_id,
                ingested_at=INGESTED_AT,
                mrn=profile.mrn,
                enterprise_patient_id=f"EPI{index:07d}",
                first_name=first_name,
                last_name=last_name,
                date_of_birth=birth_date.isoformat(),
                sex=rng.choice(["female", "male", "unknown"]),
                address_line=f"{rng.randint(100, 9999)} {rng.choice(STREETS)} St",
                city=rng.choice(INDIANA_CITIES),
                state="IN",
                postal_code=str(rng.randint(46000, 46999)),
                phone=f"317-555-{rng.randint(1000, 9999)}",
                email=f"{first_name.lower()}.{last_name.lower()}{index}@example.test",
            )
        )
        counts["raw_patients"] += 1

        for enc_position, encounter_number in enumerate(profile.encounter_numbers, start=1):
            encounter_date = start_date + timedelta(days=rng.randint(0, 720))
            department_code = choose_department(profile.conditions, department_codes, rng)
            provider_id = rng.choice(provider_ids)
            records.append(
                RawEncounter(
                    source_system=source_system,
                    source_record_id=encounter_number,
                    ingestion_batch_id=batch_id,
                    ingested_at=INGESTED_AT,
                    encounter_number=encounter_number,
                    mrn=profile.mrn,
                    department_code=department_code,
                    attending_provider_id=provider_id,
                    encounter_type=rng.choice(["office_visit", "telehealth", "emergency", "inpatient"]),
                    admit_datetime=at_hour(encounter_date, rng.randint(6, 17)),
                    discharge_datetime=at_hour(encounter_date + timedelta(days=rng.choice([0, 0, 0, 1, 2])), rng.randint(10, 22)),
                    discharge_disposition=rng.choice(["home", "home_health", "left_without_being_seen", "transferred"]),
                    financial_class=rng.choice(["commercial", "medicare", "medicaid", "self_pay"]),
                )
            )
            counts["raw_encounters"] += 1

            if enc_position == 1:
                add_diagnoses(records, counts, profile, encounter_number, source_system, batch_id, encounter_date)
                add_allergies(records, counts, profile, rng, source_system, batch_id, encounter_date)

            add_labs(records, counts, profile, encounter_number, rng, source_system, batch_id, encounter_date)
            add_medications(records, counts, profile, encounter_number, rng, source_system, batch_id, provider_id, encounter_date)

    return records, counts


def add_diagnoses(
    records: list[object],
    counts: dict[str, int],
    profile: PatientProfile,
    encounter_number: str,
    source_system: str,
    batch_id: str,
    encounter_date: date,
) -> None:
    for ranking, condition_key in enumerate(sorted(profile.conditions), start=1):
        code, description, code_system = DIAGNOSES[condition_key]
        records.append(
            RawDiagnosis(
                source_system=source_system,
                source_record_id=f"DX-{encounter_number}-{ranking}",
                ingestion_batch_id=batch_id,
                ingested_at=INGESTED_AT,
                encounter_number=encounter_number,
                mrn=profile.mrn,
                diagnosis_code=code,
                diagnosis_description=description,
                code_system=code_system,
                diagnosis_type="active_problem",
                present_on_admission="Y",
                diagnosis_datetime=at_hour(encounter_date, 9 + ranking),
                ranking=ranking,
            )
        )
        counts["raw_diagnoses"] += 1


def add_labs(
    records: list[object],
    counts: dict[str, int],
    profile: PatientProfile,
    encounter_number: str,
    rng: random.Random,
    source_system: str,
    batch_id: str,
    encounter_date: date,
) -> None:
    if "diabetes" in profile.conditions and profile.has_a1c:
        a1c_value = round(rng.uniform(6.1, 10.8), 1)
        add_lab(records, counts, profile.mrn, encounter_number, source_system, batch_id, "4548-4", "Hemoglobin A1c", a1c_value, "%", "4.0-5.6", encounter_date)
        if profile.conflicting_labs:
            add_lab(records, counts, profile.mrn, encounter_number, source_system, batch_id, "4548-4", "Hemoglobin A1c", 5.1, "%", "4.0-5.6", encounter_date, suffix="CONFLICT")

    if "hypertension" in profile.conditions and profile.has_bp:
        systolic = rng.randint(132, 178)
        diastolic = rng.randint(78, 104)
        add_lab(records, counts, profile.mrn, encounter_number, source_system, batch_id, "BP-SYS", "Systolic blood pressure", systolic, "mmHg", "<120", encounter_date)
        add_lab(records, counts, profile.mrn, encounter_number, source_system, batch_id, "BP-DIA", "Diastolic blood pressure", diastolic, "mmHg", "<80", encounter_date)

    if rng.random() < 0.45:
        add_lab(records, counts, profile.mrn, encounter_number, source_system, batch_id, "2345-7", "Glucose", round(rng.uniform(75, 220), 0), "mg/dL", "70-99", encounter_date)
    if rng.random() < 0.35:
        add_lab(records, counts, profile.mrn, encounter_number, source_system, batch_id, "13457-7", "LDL cholesterol", round(rng.uniform(70, 190), 0), "mg/dL", "<100", encounter_date)


def add_lab(
    records: list[object],
    counts: dict[str, int],
    mrn: str,
    encounter_number: str,
    source_system: str,
    batch_id: str,
    lab_code: str,
    lab_name: str,
    value: float,
    unit: str,
    reference_range: str,
    encounter_date: date,
    suffix: Optional[str] = None,
) -> None:
    result_value = str(value).rstrip("0").rstrip(".")
    abnormal_flag = "H" if is_high_lab(lab_code, float(value)) else "N"
    record_suffix = suffix or f"{counts['raw_labs'] + 1:08d}"
    records.append(
        RawLab(
            source_system=source_system,
            source_record_id=f"LAB-{encounter_number}-{lab_code}-{record_suffix}",
            ingestion_batch_id=batch_id,
            ingested_at=INGESTED_AT,
            order_id=f"ORD-{encounter_number}-{lab_code}",
            encounter_number=encounter_number,
            mrn=mrn,
            lab_code=lab_code,
            lab_name=lab_name,
            result_value=result_value,
            result_numeric=float(value),
            result_unit=unit,
            reference_range=reference_range,
            abnormal_flag=abnormal_flag,
            result_status="final",
            collected_at=at_hour(encounter_date, 8),
            resulted_at=at_hour(encounter_date, 14),
        )
    )
    counts["raw_labs"] += 1


def add_medications(
    records: list[object],
    counts: dict[str, int],
    profile: PatientProfile,
    encounter_number: str,
    rng: random.Random,
    source_system: str,
    batch_id: str,
    provider_id: str,
    encounter_date: date,
) -> None:
    for condition_key in sorted(profile.conditions):
        if condition_key not in MEDICATIONS:
            continue
        if profile.missing_active_medication and condition_key in {"diabetes", "hypertension"}:
            continue
        if rng.random() > 0.78:
            continue

        medication_code, medication_name, dose, route, frequency = rng.choice(MEDICATIONS[condition_key])
        records.append(
            RawMedication(
                source_system=source_system,
                source_record_id=f"MED-{encounter_number}-{condition_key}",
                ingestion_batch_id=batch_id,
                ingested_at=INGESTED_AT,
                order_id=f"MEDORD-{encounter_number}-{condition_key}",
                encounter_number=encounter_number,
                mrn=profile.mrn,
                medication_code=medication_code,
                medication_name=medication_name,
                dose=dose,
                route=route,
                frequency=frequency,
                order_status="active",
                ordered_at=at_hour(encounter_date, 11),
                start_datetime=at_hour(encounter_date, 12),
                stop_datetime=None,
                ordering_provider_id=provider_id,
            )
        )
        counts["raw_medications"] += 1


def add_allergies(
    records: list[object],
    counts: dict[str, int],
    profile: PatientProfile,
    rng: random.Random,
    source_system: str,
    batch_id: str,
    encounter_date: date,
) -> None:
    if rng.random() > 0.22:
        return

    for allergy_index in range(1, rng.randint(1, 2) + 1):
        allergen_code, allergen_name, allergen_type, reaction, severity = rng.choice(ALLERGIES)
        records.append(
            RawAllergy(
                source_system=source_system,
                source_record_id=f"ALG-{profile.mrn}-{allergy_index}",
                ingestion_batch_id=batch_id,
                ingested_at=INGESTED_AT,
                mrn=profile.mrn,
                allergen_code=allergen_code,
                allergen_name=allergen_name,
                allergen_type=allergen_type,
                reaction=reaction,
                severity=severity,
                allergy_status="active",
                recorded_at=at_hour(encounter_date, 10),
            )
        )
        counts["raw_allergies"] += 1


def choose_department(conditions: set[str], department_codes: list[str], rng: random.Random) -> str:
    if "diabetes" in conditions and rng.random() < 0.45:
        return "ENDO"
    if "hypertension" in conditions and rng.random() < 0.35:
        return "CARD"
    if "ckd" in conditions and rng.random() < 0.45:
        return "NEPH"
    return rng.choice(department_codes)


def is_high_lab(lab_code: str, value: float) -> bool:
    thresholds = {
        "4548-4": 5.6,
        "BP-SYS": 120,
        "BP-DIA": 80,
        "2345-7": 99,
        "13457-7": 100,
    }
    return value > thresholds.get(lab_code, 999999)


def random_birth_date(rng: random.Random) -> date:
    age_years = rng.randint(18, 90)
    return ANCHOR_DATE - timedelta(days=(age_years * 365 + rng.randint(0, 364)))


def at_hour(day: date, hour: int) -> str:
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=timezone.utc).isoformat()


def clear_batch(db, source_system: str, batch_id: str) -> None:
    for model in (RawAllergy, RawMedication, RawLab, RawDiagnosis, RawEncounter, RawProvider, RawDepartment, RawPatient):
        db.query(model).filter(
            model.source_system == source_system,
            model.ingestion_batch_id == batch_id,
        ).delete(synchronize_session=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic operational hospital data into raw_* tables.")
    parser.add_argument("--patients", type=int, default=1000, help="Number of synthetic patients to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible synthetic data.")
    parser.add_argument(
        "--ingestion-batch-id",
        default=None,
        help="Batch identifier stamped onto every generated raw row. Defaults to synthetic-<seed>-<patients>.",
    )
    parser.add_argument(
        "--source-system",
        default=DEFAULT_SOURCE_SYSTEM,
        help="Operational source system label stamped onto every generated raw row.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.patients < 1:
        raise SystemExit("--patients must be greater than 0")

    batch_id = args.ingestion_batch_id or f"synthetic-{args.seed}-{args.patients}"
    records, counts = generate_patients(args.patients, args.seed, args.source_system, batch_id)

    db = SessionLocal()
    try:
        clear_batch(db, args.source_system, batch_id)
        db.add_all(records)
        write_audit_event(
            db,
            action="hospital_data_batch_generated",
            resource_type="ingestion_batch",
            resource_id=batch_id,
            metadata={
                "source_system": args.source_system,
                "ingestion_batch_id": batch_id,
                "patient_count": args.patients,
                "seed": args.seed,
                "table_counts": counts,
            },
            username="system",
            role="system",
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Generated synthetic hospital raw data for {args.patients} patients")
    print(f"source_system={args.source_system}")
    print(f"ingestion_batch_id={batch_id}")
    for table_name, count in counts.items():
        print(f"- {table_name}: {count}")


if __name__ == "__main__":
    main()
