import { AuthUser, Permission } from "@/lib/types";

export const TOKEN_STORAGE_KEY = "clinsight_token";
export const USER_STORAGE_KEY = "clinsight_user";

export function saveSession(token: string, user: AuthUser) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  updateStoredUser(user);
  document.cookie = `${TOKEN_STORAGE_KEY}=${token}; path=/; max-age=28800; SameSite=Lax`;
}

export function updateStoredUser(user: AuthUser) {
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearSession() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(USER_STORAGE_KEY);
  document.cookie = `${TOKEN_STORAGE_KEY}=; path=/; max-age=0; SameSite=Lax`;
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawUser = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as AuthUser;
  } catch {
    clearSession();
    return null;
  }
}

export const PERMISSION_LABELS: Record<Permission, string> = {
  view_patient_directory: "Search the patient directory",
  view_patient_charts: "Review longitudinal patient charts",
  view_grounded_ai_summary: "View grounded clinical summaries",
  view_care_gaps: "Review care-gap suggestions",
  view_quality_alerts: "Review patient data-quality alerts",
  view_source_metadata: "View clinical source metadata",
  view_patient_chat: "Ask chart-grounded questions",
  upload_fhir_bundle: "Upload FHIR patient records",
  import_external_fhir: "Import patients from SMART Health IT",
  investigate_ingestion: "Investigate ingestion and quarantine failures",
  view_audit_logs: "Review user audit activity",
  view_pipeline_runs: "Review pipeline-run metrics",
  record_dbt_transformation_audit: "Record dbt transformation audit events",
  view_demo_users: "View demo-role information",
};

export function hasPermission(user: AuthUser, permission: Permission) {
  return user.permissions.includes(permission);
}

export function canUpload(user: AuthUser) {
  return hasPermission(user, "upload_fhir_bundle");
}

export function canImportExternalFhir(user: AuthUser) {
  return hasPermission(user, "import_external_fhir");
}

export function canViewInsights(user: AuthUser) {
  return hasPermission(user, "view_grounded_ai_summary");
}

export function canViewCareGaps(user: AuthUser) {
  return hasPermission(user, "view_care_gaps");
}

export function canViewQuality(user: AuthUser) {
  return hasPermission(user, "view_quality_alerts");
}

export function canViewSourceMetadata(user: AuthUser) {
  return hasPermission(user, "view_source_metadata");
}

export function canViewAuditLogs(user: AuthUser) {
  return hasPermission(user, "view_audit_logs");
}

export function canInvestigateIngestion(user: AuthUser) {
  return hasPermission(user, "investigate_ingestion");
}
