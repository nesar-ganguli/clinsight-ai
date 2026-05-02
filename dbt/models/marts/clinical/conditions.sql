with diagnoses as (
    select * from {{ ref('stg_diagnoses') }}
)

select
    {{ stable_bigint_id("diagnosis_record_id") }} as id,
    diagnosis_record_id as clinical_condition_id,
    {{ stable_bigint_id("patient_id") }} as patient_id,
    null::text as fhir_condition_id,
    diagnosis_code as condition_code,
    diagnosis_description as condition_name,
    case
        when diagnosis_type in ('active_problem', 'admitting', 'principal') then 'active'
        when diagnosis_type in ('resolved', 'inactive') then 'resolved'
        else 'active'
    end as clinical_status,
    diagnosis_datetime::date as onset_date,
    source_system,
    diagnosis_source_id as source_record_id,
    ingestion_batch_id,
    ingested_at,
    patient_id as source_patient_id,
    encounter_id as source_encounter_id,
    code_system,
    present_on_admission,
    diagnosis_rank
from diagnoses
