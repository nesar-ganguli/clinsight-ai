with encounters as (
    select * from {{ ref('stg_encounters') }}
)

select
    {{ stable_bigint_id("encounter_record_id") }} as id,
    encounter_record_id as clinical_encounter_id,
    {{ stable_bigint_id("patient_id") }} as patient_id,
    null::text as fhir_encounter_id,
    case
        when discharge_datetime is not null then 'finished'
        when admit_datetime is not null then 'in-progress'
        else 'unknown'
    end as status,
    'hospital' as encounter_class,
    encounter_type,
    admit_datetime as period_start,
    discharge_datetime as period_end,
    source_system,
    source_record_id,
    ingestion_batch_id,
    ingested_at,
    patient_id as source_patient_id,
    encounter_id as source_encounter_id,
    department_code,
    attending_provider_id,
    discharge_disposition,
    financial_class
from encounters
