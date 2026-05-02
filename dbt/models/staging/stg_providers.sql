with source as (
    select * from {{ source('raw_hospital', 'raw_providers') }}
)

select
    md5(concat_ws('|', source_system, ingestion_batch_id, source_record_id)) as provider_record_id,
    nullif(trim(provider_id), '') as provider_id,
    nullif(trim(npi), '') as npi,
    initcap(nullif(trim(first_name), '')) as first_name,
    initcap(nullif(trim(last_name), '')) as last_name,
    nullif(trim(concat_ws(' ', nullif(first_name, ''), nullif(last_name, ''))), '') as provider_name,
    upper(nullif(trim(credentials), '')) as credentials,
    initcap(nullif(trim(specialty), '')) as specialty,
    upper(nullif(trim(department_code), '')) as department_code,
    lower(nullif(trim(employment_status), '')) as employment_status,
    lower(nullif(trim(source_system), '')) as source_system,
    nullif(trim(source_record_id), '') as source_record_id,
    nullif(trim(ingestion_batch_id), '') as ingestion_batch_id,
    ingested_at::timestamp as ingested_at
from source
