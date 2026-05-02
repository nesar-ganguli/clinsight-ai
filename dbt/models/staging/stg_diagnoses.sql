with source as (
    select * from {{ source('raw_hospital', 'raw_diagnoses') }}
)

select
    md5(concat_ws('|', source_system, ingestion_batch_id, source_record_id)) as diagnosis_record_id,
    nullif(trim(source_record_id), '') as diagnosis_source_id,
    nullif(trim(encounter_number), '') as encounter_id,
    nullif(trim(mrn), '') as patient_id,
    upper(nullif(trim(diagnosis_code), '')) as diagnosis_code,
    initcap(nullif(trim(diagnosis_description), '')) as diagnosis_description,
    upper(replace(nullif(trim(code_system), ''), '-', '_')) as code_system,
    lower(nullif(trim(diagnosis_type), '')) as diagnosis_type,
    case
        when upper(trim(present_on_admission)) in ('Y', 'YES', 'TRUE') then true
        when upper(trim(present_on_admission)) in ('N', 'NO', 'FALSE') then false
        else null
    end as present_on_admission,
    nullif(trim(diagnosis_datetime), '')::timestamp as diagnosis_datetime,
    ranking::integer as diagnosis_rank,
    lower(nullif(trim(source_system), '')) as source_system,
    nullif(trim(ingestion_batch_id), '') as ingestion_batch_id,
    ingested_at::timestamp as ingested_at
from source
