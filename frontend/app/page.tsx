"use client";

import Link from "next/link";
import { useState } from "react";

import { DemoUsersPanel } from "@/components/demo-users-panel";
import { PatientListPanel } from "@/components/patient-list-panel";
import { UploadPanel } from "@/components/upload-panel";
import { UploadResponse } from "@/lib/types";

export default function HomePage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [latestUpload, setLatestUpload] = useState<UploadResponse | null>(null);

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
          <UploadPanel onUploaded={handleUploaded} />
        </div>
        <div className="stack">
          <PatientListPanel refreshKey={refreshKey} />
          <DemoUsersPanel />
        </div>
      </section>
    </main>
  );
}
