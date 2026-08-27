export type SourceMetadata = {
  source_type: string | null;
  source_system: string | null;
  source_record_id: string | null;
  ingestion_batch_id: string | null;
  transformed_at: string | null;
};

export type PatientSummary = SourceMetadata & {
  id: number;
  fhir_patient_id: string | null;
  full_name: string | null;
  gender: string | null;
  birth_date: string | null;
};

export type Condition = SourceMetadata & {
  id: number;
  fhir_condition_id: string | null;
  condition_code: string | null;
  condition_name: string | null;
  clinical_status: string | null;
  onset_date: string | null;
};

export type Observation = SourceMetadata & {
  id: number;
  fhir_observation_id: string | null;
  observation_code: string | null;
  observation_name: string | null;
  value: string | null;
  unit: string | null;
  effective_date: string | null;
};

export type Encounter = SourceMetadata & {
  id: number;
  fhir_encounter_id: string | null;
  status: string | null;
  encounter_class: string | null;
  encounter_type: string | null;
  period_start: string | null;
  period_end: string | null;
};

export type MedicationRequest = SourceMetadata & {
  id: number;
  fhir_medication_request_id: string | null;
  status: string | null;
  intent: string | null;
  medication_code: string | null;
  medication_name: string | null;
  authored_on: string | null;
};

export type AllergyIntolerance = SourceMetadata & {
  id: number;
  fhir_allergy_id: string | null;
  clinical_status: string | null;
  verification_status: string | null;
  allergy_code: string | null;
  allergy_name: string | null;
  criticality: string | null;
  recorded_date: string | null;
};

export type Patient = PatientSummary & {
  conditions: Condition[];
  observations: Observation[];
  encounters: Encounter[];
  medication_requests: MedicationRequest[];
  allergies: AllergyIntolerance[];
};

export type PatientListResponse = {
  items: PatientSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type UploadResponse = {
  message: string;
  patient_id: number;
  import_mode: "created" | "updated";
  resource_counts: Record<string, number>;
  ingestion_summary: {
    accepted: number;
    rejected: number;
    unsupported: number;
  };
};

export type ExternalFhirPatientSummary = {
  id: string;
  full_name: string | null;
  gender: string | null;
  birth_date: string | null;
};

export type ExternalFhirPatientListResponse = {
  items: ExternalFhirPatientSummary[];
  total: number;
  source_system: string;
  fhir_base_url: string;
};

export type ExternalFhirImportResponse = UploadResponse & {
  source_system: string;
  external_patient_id: string;
};

export type QualityAlert = {
  code: string;
  severity: "critical" | "warning" | "info";
  category: string;
  field: string;
  message: string;
};

export type QualityAlertsResponse = {
  patient_id: number;
  alerts: QualityAlert[];
};

export type InsightCitation = SourceMetadata & {
  id: string;
  resource_type: string;
  record_id: number;
  fhir_id: string | null;
  label: string;
  date: string | null;
  excerpt: string;
};

export type SupportedClaim = {
  id: string;
  text: string;
  citation_ids: string[];
};

export type SummarySection = {
  title: string;
  claims: SupportedClaim[];
};

export type ChartInconsistency = {
  code: string;
  severity: "critical" | "warning" | "info";
  title: string;
  explanation: string;
  citation_ids: string[];
};

export type CareGapSuggestion = {
  code: string;
  priority: "high" | "medium" | "low";
  title: string;
  recommendation: string;
  rationale: string;
  citation_ids: string[];
};

export type InsightEvaluation = {
  grounded_claims: number;
  unsupported_claims: number;
  unresolved_citations: number;
  source_coverage: number;
  hallucination_risk: "low" | "medium" | "high";
  checks: string[];
};

export type PatientAiInsightsResponse = {
  patient_id: number;
  generated_by: string;
  disclaimer: string;
  summary_sections: SummarySection[];
  inconsistencies: ChartInconsistency[];
  care_gaps: CareGapSuggestion[];
  citations: InsightCitation[];
  evaluation: InsightEvaluation;
};

export type PatientChatResponse = {
  patient_id: number;
  question: string;
  answer: string;
  confidence: "high" | "medium" | "low";
  generated_by: string;
  retrieval_strategy: string;
  citations: InsightCitation[];
  safety_notes: string[];
  refused: boolean;
  validation_errors: string[];
  llm_used: boolean;
};

export type DemoUser = {
  id: string;
  name: string;
  role: string;
  focus: string;
  permissions: string[];
};

export type DemoUsersResponse = {
  users: DemoUser[];
};

export type UserRole = "admin" | "clinician" | "care_coordinator" | "data_reviewer";

export type Permission =
  | "view_patient_directory"
  | "view_patient_charts"
  | "view_grounded_ai_summary"
  | "view_care_gaps"
  | "view_quality_alerts"
  | "view_source_metadata"
  | "view_patient_chat"
  | "upload_fhir_bundle"
  | "import_external_fhir"
  | "investigate_ingestion"
  | "view_audit_logs"
  | "view_pipeline_runs"
  | "record_dbt_transformation_audit"
  | "view_demo_users";

export type AuthUser = {
  id: number;
  username: string;
  full_name: string | null;
  role: UserRole;
  permissions: Permission[];
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type DemoAuthAccount = {
  username: string;
  full_name: string | null;
  role: UserRole;
  permissions: Permission[];
};

export type DemoAuthAccountListResponse = {
  items: DemoAuthAccount[];
};

export type AuditLog = {
  id: number;
  user_id: number | null;
  username: string | null;
  role: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  patient_id: number | null;
  event_timestamp: string;
  metadata: Record<string, unknown>;
};

export type AuditLogListResponse = {
  items: AuditLog[];
  total: number;
  limit: number;
  offset: number;
};

export type IngestionBatch = {
  id: number;
  source_system_id: number;
  source_system_name: string;
  source_system_type: string;
  ingestion_type: string;
  filename: string | null;
  status: string;
  record_count: number;
  accepted_count: number;
  rejected_count: number;
  quarantine_count: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
};

export type IngestionBatchListResponse = {
  items: IngestionBatch[];
  total: number;
  limit: number;
  offset: number;
};

export type QuarantineRecordSummary = {
  id: number;
  ingestion_batch_id: number;
  source_system_id: number;
  resource_type: string;
  source_record_id: string | null;
  error_code: string;
  error_message: string;
  created_at: string;
};

export type QuarantineRecordListResponse = {
  items: QuarantineRecordSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type QuarantinePayload = {
  id: number;
  ingestion_batch_id: number;
  raw_payload: unknown;
};
