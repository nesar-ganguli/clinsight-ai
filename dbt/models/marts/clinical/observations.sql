with labs as (
    select * from {{ ref('stg_labs') }}
)

select
    {{ stable_bigint_id("lab_record_id") }} as id,
    lab_record_id as clinical_observation_id,
    {{ stable_bigint_id("patient_id") }} as patient_id,
    null::text as fhir_observation_id,
    lab_code as observation_code,
    lab_name as observation_name,
    result_value as value,
    result_unit as unit,
    coalesce(resulted_at, collected_at) as effective_date,
    case
        when result_status in ('final', 'corrected', 'preliminary', 'amended') then result_status
        else 'unknown'
    end as status,
    'hospital_database'::text as source_type,
    source_system,
    lab_source_id as source_record_id,
    ingestion_batch_id,
    current_timestamp as transformed_at,
    ingested_at,
    patient_id as source_patient_id,
    encounter_id as source_encounter_id,
    order_id,
    result_numeric,
    reference_range,
    abnormal_flag
from labs
