with source as (
    select * from {{ source('raw_hospital', 'raw_encounters') }}
)

select
    md5(concat_ws('|', source_system, ingestion_batch_id, source_record_id)) as encounter_record_id,
    nullif(trim(encounter_number), '') as encounter_id,
    nullif(trim(mrn), '') as patient_id,
    upper(nullif(trim(department_code), '')) as department_code,
    nullif(trim(attending_provider_id), '') as attending_provider_id,
    lower(nullif(trim(source_system), '')) as source_system,
    nullif(trim(source_record_id), '') as source_record_id,
    nullif(trim(ingestion_batch_id), '') as ingestion_batch_id,
    ingested_at::timestamp as ingested_at,
    lower(nullif(trim(encounter_type), '')) as encounter_type,
    nullif(trim(admit_datetime), '')::timestamp as admit_datetime,
    nullif(trim(discharge_datetime), '')::timestamp as discharge_datetime,
    lower(nullif(trim(discharge_disposition), '')) as discharge_disposition,
    lower(nullif(trim(financial_class), '')) as financial_class
from source
