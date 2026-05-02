with source as (
    select * from {{ source('raw_hospital', 'raw_departments') }}
)

select
    md5(concat_ws('|', source_system, ingestion_batch_id, source_record_id)) as department_record_id,
    upper(nullif(trim(department_code), '')) as department_code,
    initcap(nullif(trim(department_name), '')) as department_name,
    upper(nullif(trim(facility_code), '')) as facility_code,
    initcap(nullif(trim(facility_name), '')) as facility_name,
    initcap(nullif(trim(service_line), '')) as service_line,
    lower(nullif(trim(location_type), '')) as location_type,
    case
        when upper(trim(active_flag)) in ('Y', 'YES', 'TRUE', 'ACTIVE') then true
        when upper(trim(active_flag)) in ('N', 'NO', 'FALSE', 'INACTIVE') then false
        else null
    end as is_active,
    lower(nullif(trim(source_system), '')) as source_system,
    nullif(trim(source_record_id), '') as source_record_id,
    nullif(trim(ingestion_batch_id), '') as ingestion_batch_id,
    ingested_at::timestamp as ingested_at
from source
