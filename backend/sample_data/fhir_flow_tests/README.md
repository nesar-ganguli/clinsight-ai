# FHIR Ingestion Flow Test Bundles

These files exercise the validation, identity, update, quarantine, unsupported-resource, and batch-failure paths implemented by ClinSight. Upload them one at a time through the UI or `POST /api/upload` and inspect `ingestion_batches`, `pipeline_runs`, `quarantine_records`, `patient_source_identifiers`, and the clinical tables after each attempt.

The files test this application's supported FHIR subset; they are not a general FHIR conformance suite.

## Scenarios

| File | Upload result | Expected ingestion result |
| --- | --- | --- |
| `01_valid_create_then_exact_reupload.json` | Upload twice | First upload is `created`; second is `updated`. Each accepts 3 and rejects 0. The second pipeline run reports `duplicate_or_updated_count = 3`, with no duplicate clinical rows. |
| `02_partial_success_quarantine_and_unsupported.json` | HTTP 200 | Received 7; accepted 3 (Patient, Condition, Allergy); rejected/quarantined 3; unsupported 1 (Practitioner). Quarantine codes are `invalid_datetime`, `patient_reference_mismatch`, and `missing_status`. |
| `03_batch_fatal_no_patient.json` | HTTP 400 | `No usable Patient resource found in bundle`. The ingestion batch and pipeline run persist as `failed`; no clinical or quarantine rows from the attempt persist. |
| `04_additional_patient_quarantined.json` | HTTP 200 | Received 3; accepted 2 (first Patient and Observation); rejected 1 with `additional_patient_not_supported`. |
| `05_malformed_entries_quarantined.json` | HTTP 200 | Received 4; accepted 2 (Patient and Condition); rejected 2 with `malformed_bundle_entry` and `missing_resource_type`. |
| `06_unsupported_resources_counted_not_quarantined.json` | HTTP 200 | Received 4; accepted 2 (Patient and Observation); rejected 0; unsupported 2 (Practitioner and Organization); no quarantine rows. |
| `07a_default_source_same_patient_id.json` then `07b_smart_source_same_patient_id_creates_separate_patient.json` | Both HTTP 200 | The same FHIR patient ID is stored as two canonical patients because the second Bundle declares the SMART sandbox source. Two source-identifier mappings exist under different source systems. |
| `08a_same_source_initial_with_two_conditions.json` then `08b_same_source_update_omits_existing_condition.json` | Both HTTP 200 | The second upload updates the patient name and first Condition, while the omitted second Condition remains stored. Omission is not deletion. |
| `09_batch_fatal_patient_missing_id.json` | HTTP 400 | The Patient is quarantinable during parsing but no usable Patient remains, so the whole attempt fails and the clinical/quarantine transaction rolls back. The durable batch/run rejected count equals the 2-entry envelope count. |

## Inspect the latest attempt

```sql
SELECT *
FROM ingestion_batches
ORDER BY id DESC
LIMIT 1;

SELECT *
FROM pipeline_runs
ORDER BY id DESC
LIMIT 1;

SELECT resource_type, source_record_id, error_code, error_message
FROM quarantine_records
WHERE ingestion_batch_id = (SELECT MAX(id) FROM ingestion_batches)
ORDER BY id;
```

`unsupported_count` is returned in the upload response and copied into upload audit metadata, but it does not have a dedicated column in `ingestion_batches` or `pipeline_runs`.

## Inspect identity behavior for scenario 07

```sql
SELECT
    p.id AS canonical_patient_id,
    p.full_name,
    ss.name AS source_system,
    psi.identifier_value
FROM patient_source_identifiers psi
JOIN patients p ON p.id = psi.patient_id
JOIN source_systems ss ON ss.id = psi.source_system_id
WHERE psi.identifier_value = 'flow-shared-patient-id'
ORDER BY p.id;
```

## Inspect retention behavior for scenario 08

```sql
SELECT id, full_name
FROM patients
WHERE fhir_patient_id = 'flow-update-retain-001';

SELECT
    fhir_condition_id,
    condition_name,
    clinical_status,
    ingestion_batch_id
FROM conditions
WHERE patient_id = (
    SELECT id
    FROM patients
    WHERE fhir_patient_id = 'flow-update-retain-001'
)
ORDER BY fhir_condition_id;
```

Expected after `08b`: the patient name changes from `Olivia Bennett` to `Olivia Carter`; `flow-update-condition-retained` is resolved and renamed; `flow-update-condition-omitted-later` still exists with its earlier batch metadata.
