with allergies as (
    select * from {{ ref('stg_allergies') }}
)

select
    {{ stable_bigint_id("allergy_record_id") }} as id,
    allergy_record_id as clinical_allergy_id,
    {{ stable_bigint_id("patient_id") }} as patient_id,
    null::text as fhir_allergy_id,
    case
        when allergy_status in ('active', 'inactive', 'resolved') then allergy_status
        else 'active'
    end as clinical_status,
    'confirmed' as verification_status,
    allergen_code as allergy_code,
    allergen_name as allergy_name,
    case
        when severity in ('severe', 'moderate') then 'high'
        when severity = 'mild' then 'low'
        else 'unable-to-assess'
    end as criticality,
    timezone('UTC', recorded_at) as recorded_date,
    'hospital_database'::text as source_type,
    source_system,
    allergy_source_id as source_record_id,
    ingestion_batch_id,
    current_timestamp as transformed_at,
    ingested_at,
    patient_id as source_patient_id,
    allergen_type,
    reaction,
    severity
from allergies
