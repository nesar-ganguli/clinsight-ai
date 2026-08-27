import Link from "next/link";

import { hasPermission, PERMISSION_LABELS } from "@/lib/auth";
import { AuthUser, Permission, UploadResponse, UserRole } from "@/lib/types";


const ROLE_PRESENTATION: Record<UserRole, {label: string; focus: string; featuredPermissions: Permission[]}> = {
  admin: {
    label: "Administrator",
    focus: "Clinical review and data-operations access across the workspace.",
    featuredPermissions: [
      "view_patient_charts",
      "upload_fhir_bundle",
      "investigate_ingestion",
      "view_audit_logs",
    ],
  },
  data_reviewer: {
    label: "Data reviewer",
    focus: "Data-quality, provenance, and ingestion-operations access.",
    featuredPermissions: [
      "view_source_metadata",
      "upload_fhir_bundle",
      "investigate_ingestion",
      "view_audit_logs",
    ],
  },
  clinician: {
    label: "Clinician",
    focus: "Clinical chart review with grounded summaries and record-based questions.",
    featuredPermissions: [
      "view_patient_directory",
      "view_patient_charts",
      "view_grounded_ai_summary",
      "view_patient_chat",
    ],
  },
  care_coordinator: {
    label: "Care coordinator",
    focus: "Patient review focused on care gaps and follow-up preparation.",
    featuredPermissions: [
      "view_patient_directory",
      "view_patient_charts",
      "view_care_gaps",
      "view_patient_chat",
    ],
  },
};


export function WorkspaceWelcome({user, latestUpload}: {user: AuthUser | null; latestUpload: UploadResponse | null}) {
  if (!user) {
    return (
      <section className="workspace-overview">
        <div className="workspace-welcome-copy">
          <span className="workspace-overview-eyebrow">ClinSight AI Workspace</span>
          <h1>Clinical chart review with data-quality context.</h1>
          <p>Sign in with a demo role to search patient charts and access the workflows assigned to that role.</p>
        </div>
        <aside className="access-summary signed-out-access" aria-label="Sign-in guidance">
          <span className="section-kicker">Protected workspace</span>
          <h2>Choose your role to begin</h2>
          <p>Navigation and clinical tools adapt to the authenticated account.</p>
          <Link href="/login" className="button button-primary">Sign in</Link>
        </aside>
      </section>
    );
  }

  const presentation = ROLE_PRESENTATION[user.role];
  const firstName = (user.full_name || user.username).trim().split(/\s+/)[0];
  const capabilities = presentation.featuredPermissions
    .filter((permission) => hasPermission(user, permission))
    .map((permission) => PERMISSION_LABELS[permission]);

  return (
    <section className="workspace-overview">
      <div className="workspace-welcome-copy">
        <span className="workspace-overview-eyebrow">{presentation.label} workspace</span>
        <h1>Welcome back, {firstName}.</h1>
        <p>{presentation.focus}</p>

        {latestUpload ? (
          <div className="latest-import-card" aria-live="polite">
            <div>
              <span className="section-kicker">Latest import</span>
              <strong>Patient #{latestUpload.patient_id} was {latestUpload.import_mode}.</strong>
            </div>
            <Link href={`/patients/${latestUpload.patient_id}`} className="button button-primary">
              Open patient chart
            </Link>
          </div>
        ) : null}
      </div>

      <aside className="access-summary" aria-label={`Access available to ${presentation.label}`}>
        <div className="access-summary-heading">
          <div>
            <span className="section-kicker">Your access</span>
            <h2>{presentation.label}</h2>
          </div>
          <span className="access-status">Active</span>
        </div>
        <ul className="access-list">
          {capabilities.map((capability) => (
            <li key={capability}><span aria-hidden="true">✓</span>{capability}</li>
          ))}
        </ul>
      </aside>
    </section>
  );
}
