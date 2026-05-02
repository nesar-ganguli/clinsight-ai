with source as (
    select * from {{ source('raw_hospital', 'raw_medications') }}
)

select
    md5(concat_ws('|', source_system, ingestion_batch_id, source_record_id)) as medication_record_id,
    nullif(trim(source_record_id), '') as medication_source_id,
    nullif(trim(order_id), '') as order_id,
    nullif(trim(encounter_number), '') as encounter_id,
    nullif(trim(mrn), '') as patient_id,
    upper(nullif(trim(medication_code), '')) as medication_code,
    initcap(nullif(trim(medication_name), '')) as medication_name,
    lower(nullif(trim(dose), '')) as dose,
    lower(nullif(trim(route), '')) as route,
    lower(nullif(trim(frequency), '')) as frequency,
    lower(nullif(trim(order_status), '')) as order_status,
    nullif(trim(ordered_at), '')::timestamp as ordered_at,
    nullif(trim(start_datetime), '')::timestamp as start_datetime,
    nullif(trim(stop_datetime), '')::timestamp as stop_datetime,
    nullif(trim(ordering_provider_id), '') as ordering_provider_id,
    lower(nullif(trim(source_system), '')) as source_system,
    nullif(trim(ingestion_batch_id), '') as ingestion_batch_id,
    ingested_at::timestamp as ingested_at
from source
