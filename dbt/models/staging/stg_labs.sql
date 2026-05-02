with source as (
    select * from {{ source('raw_hospital', 'raw_labs') }}
)

select
    md5(concat_ws('|', source_system, ingestion_batch_id, source_record_id)) as lab_record_id,
    nullif(trim(source_record_id), '') as lab_source_id,
    nullif(trim(order_id), '') as order_id,
    nullif(trim(encounter_number), '') as encounter_id,
    nullif(trim(mrn), '') as patient_id,
    upper(nullif(trim(lab_code), '')) as lab_code,
    initcap(nullif(trim(lab_name), '')) as lab_name,
    nullif(trim(result_value), '') as result_value,
    result_numeric::numeric as result_numeric,
    nullif(trim(result_unit), '') as result_unit,
    nullif(trim(reference_range), '') as reference_range,
    upper(nullif(trim(abnormal_flag), '')) as abnormal_flag,
    lower(nullif(trim(result_status), '')) as result_status,
    nullif(trim(collected_at), '')::timestamp as collected_at,
    nullif(trim(resulted_at), '')::timestamp as resulted_at,
    lower(nullif(trim(source_system), '')) as source_system,
    nullif(trim(ingestion_batch_id), '') as ingestion_batch_id,
    ingested_at::timestamp as ingested_at
from source
