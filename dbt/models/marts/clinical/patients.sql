with ranked_patients as (
    select
        *,
        row_number() over (
            partition by patient_id
            order by ingested_at desc, ingestion_batch_id desc, source_record_id desc
        ) as patient_rank
    from {{ ref('stg_patients') }}
)

select
    {{ stable_bigint_id("patient_id") }} as id,
    md5(patient_id) as clinical_patient_id,
    null::text as fhir_patient_id,
    full_name,
    sex as gender,
    birth_date,
    source_system,
    source_record_id,
    ingestion_batch_id,
    ingested_at,
    patient_id as source_patient_id,
    enterprise_patient_id
from ranked_patients
where patient_rank = 1
