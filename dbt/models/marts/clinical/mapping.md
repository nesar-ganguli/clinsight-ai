{% docs clinical_mapping %}

# Clinical Curated Mapping

The clinical marts transform hospital operational staging views into app-shaped clinical concepts. They do not write into the FastAPI application tables directly; they produce a compatible curated projection that can be loaded into the existing SQLAlchemy tables in a later step.

| Curated model | Source staging model | App concept | Mapping notes |
| --- | --- | --- | --- |
| `patients` | `stg_patients` | `Patient` | MRN is converted to a stable numeric `id`; demographics map to `full_name`, `gender`, and `birth_date`. |
| `encounters` | `stg_encounters` | `Encounter` | Encounter number becomes source encounter id; admission/discharge timestamps map to `period_start` and `period_end`. |
| `conditions` | `stg_diagnoses` | `Condition` | Diagnosis code/description map to `condition_code` and `condition_name`; active operational diagnoses map to active clinical conditions. |
| `observations` | `stg_labs` | `Observation` | Lab and vital rows map to observations; lab code/name/value/unit map to observation code/name/value/unit. |
| `medication_requests` | `stg_medications` | `MedicationRequest` | Medication orders map to medication requests with intent `order` and normalized order status. |
| `allergies` | `stg_allergies` | `AllergyIntolerance` | Operational allergies map to allergy code/name/status, verification status, criticality, and recorded date. |

All curated models preserve source traceability with `source_type`, `source_system`, `source_record_id`, `ingestion_batch_id`, `transformed_at`, and `ingested_at`. Hospital operational rows use `source_type = 'hospital_database'`. Stable generated IDs are derived from staging record identifiers with deterministic hashes so reruns for the same raw batch produce the same curated keys.

{% enddocs %}
