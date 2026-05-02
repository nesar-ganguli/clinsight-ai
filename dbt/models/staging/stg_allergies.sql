with source as (
    select * from {{ source('raw_hospital', 'raw_allergies') }}
)

select
    md5(concat_ws('|', source_system, ingestion_batch_id, source_record_id)) as allergy_record_id,
    nullif(trim(source_record_id), '') as allergy_source_id,
    nullif(trim(mrn), '') as patient_id,
    upper(nullif(trim(allergen_code), '')) as allergen_code,
    initcap(nullif(trim(allergen_name), '')) as allergen_name,
    lower(nullif(trim(allergen_type), '')) as allergen_type,
    lower(nullif(trim(reaction), '')) as reaction,
    lower(nullif(trim(severity), '')) as severity,
    lower(nullif(trim(allergy_status), '')) as allergy_status,
    nullif(trim(recorded_at), '')::timestamp as recorded_at,
    lower(nullif(trim(source_system), '')) as source_system,
    nullif(trim(ingestion_batch_id), '') as ingestion_batch_id,
    ingested_at::timestamp as ingested_at
from source
