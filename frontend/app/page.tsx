"use client";

import Link from "next/link";
import { useState } from "react";

import { DemoUsersPanel } from "@/components/demo-users-panel";
import { PatientListPanel } from "@/components/patient-list-panel";
import { UploadPanel } from "@/components/upload-panel";
import { canUpload, clearSession, getStoredUser } from "@/lib/auth";
import { AuthUser, UploadResponse } from "@/lib/types";

export default function HomePage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [latestUpload, setLatestUpload] = useState<UploadResponse | null>(null);
  const [user, setUser] = useState<AuthUser | null>(() => getStoredUser());

  function handleUploaded(result: UploadResponse) {
    setLatestUpload(result);
    setRefreshKey((current) => current + 1);
  }

  return (
    <main className="shell">
      <section className="hero">
        <span className="eyebrow">ClinSight AI Workspace</span>
        <h1>Clinical chart review with data quality signals built in.</h1>
        <p>
          Import FHIR bundles, search patients, and move from ingestion to longitudinal review without leaving the app.
          This Phase 2 shell turns the backend platform into a visible product flow.
        </p>
        <div className="pill-row">
          {user ? (
            <>
              <span className="pill">{user.full_name || user.username}</span>
              <span className="pill">{user.role.replaceAll("_", " ")}</span>
              <button
                className="pill"
                type="button"
                onClick={() => {
                  clearSession();
                  setUser(null);
                }}
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login" className="pill">Sign in</Link>
          )}
        </div>
        {latestUpload ? (
          <div className="pill-row">
            <span className="pill">Latest import: patient #{latestUpload.patient_id}</span>
            <Link href={`/patients/${latestUpload.patient_id}`} className="pill">
              Open patient chart
            </Link>
          </div>
        ) : null}
      </section>

      <section className="dashboard-grid">
        <div className="stack">
          {user && canUpload(user.role) ? (
            <UploadPanel onUploaded={handleUploaded} />
          ) : (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Import FHIR Bundle</h2>
                  <p className="panel-copy">Admin or data reviewer access is required for ingestion tools.</p>
                </div>
              </div>
            </section>
          )}
        </div>
        <div className="stack">
          {user ? (
            <PatientListPanel refreshKey={refreshKey} />
          ) : (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Patient Directory</h2>
                  <p className="panel-copy">Sign in to search patient charts.</p>
                </div>
              </div>
            </section>
          )}
          {user ? <DemoUsersPanel /> : null}
        </div>
      </section>
    </main>
  );
}
