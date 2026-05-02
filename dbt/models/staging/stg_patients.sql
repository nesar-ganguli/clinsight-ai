with source as (
    select * from {{ source('raw_hospital', 'raw_patients') }}
)

select
    md5(concat_ws('|', source_system, ingestion_batch_id, source_record_id)) as patient_record_id,
    nullif(trim(mrn), '') as patient_id,
    nullif(trim(enterprise_patient_id), '') as enterprise_patient_id,
    lower(nullif(trim(source_system), '')) as source_system,
    nullif(trim(source_record_id), '') as source_record_id,
    nullif(trim(ingestion_batch_id), '') as ingestion_batch_id,
    ingested_at::timestamp as ingested_at,
    initcap(nullif(trim(first_name), '')) as first_name,
    initcap(nullif(trim(last_name), '')) as last_name,
    nullif(trim(concat_ws(' ', nullif(first_name, ''), nullif(last_name, ''))), '') as full_name,
    nullif(trim(date_of_birth), '')::date as birth_date,
    case
        when lower(trim(sex)) in ('female', 'f') then 'female'
        when lower(trim(sex)) in ('male', 'm') then 'male'
        when lower(trim(sex)) in ('unknown', 'other') then lower(trim(sex))
        else nullif(lower(trim(sex)), '')
    end as sex,
    nullif(trim(address_line), '') as address_line,
    initcap(nullif(trim(city), '')) as city,
    upper(nullif(trim(state), '')) as state,
    nullif(trim(postal_code), '') as postal_code,
    nullif(trim(phone), '') as phone,
    lower(nullif(trim(email), '')) as email
from source
