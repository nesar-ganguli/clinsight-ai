with medications as (
    select * from {{ ref('stg_medications') }}
)

select
    {{ stable_bigint_id("medication_record_id") }} as id,
    medication_record_id as clinical_medication_request_id,
    {{ stable_bigint_id("patient_id") }} as patient_id,
    null::text as fhir_medication_request_id,
    case
        when order_status in ('active', 'completed', 'stopped', 'cancelled', 'on-hold', 'entered-in-error') then order_status
        else 'unknown'
    end as status,
    'order' as intent,
    medication_code,
    medication_name,
    ordered_at as authored_on,
    source_system,
    medication_source_id as source_record_id,
    ingestion_batch_id,
    ingested_at,
    patient_id as source_patient_id,
    encounter_id as source_encounter_id,
    order_id,
    dose,
    route,
    frequency,
    start_datetime,
    stop_datetime,
    ordering_provider_id
from medications
