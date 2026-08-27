"use client";

import { useEffect, useState } from "react";

import { DataIntakePanel } from "@/components/data-intake-panel";
import { PatientListPanel } from "@/components/patient-list-panel";
import { WorkspaceHeader } from "@/components/workspace-header";
import { WorkspaceWelcome } from "@/components/workspace-welcome";
import { getCurrentUser } from "@/lib/api";
import {
  canImportExternalFhir,
  canUpload,
  clearSession,
  getStoredUser,
  updateStoredUser,
} from "@/lib/auth";
import { AuthUser, UploadResponse } from "@/lib/types";

export default function HomePage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [latestUpload, setLatestUpload] = useState<UploadResponse | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    let active = true;
    const storedUser = getStoredUser();
    setUser(storedUser);

    if (storedUser) {
      void getCurrentUser()
        .then((currentUser) => {
          if (active) {
            updateStoredUser(currentUser);
            setUser(currentUser);
          }
        })
        .catch(() => {
          if (active) {
            clearSession();
            setUser(null);
          }
        })
        .finally(() => {
          if (active) {
            setSessionReady(true);
          }
        });
    } else {
      setSessionReady(true);
    }

    return () => {
      active = false;
    };
  }, []);

  function handleUploaded(result: UploadResponse) {
    setLatestUpload(result);
    setRefreshKey((current) => current + 1);
  }

  const canAccessDataIntake = Boolean(
    user && canUpload(user) && canImportExternalFhir(user),
  );

  if (!sessionReady) {
    return (
      <main className="shell">
        <section className="workspace-session-loading" role="status" aria-live="polite">
          <span className="workspace-loading-mark" aria-hidden="true">C</span>
          <div>
            <strong>Loading your ClinSight workspace</strong>
            <p>Confirming your account and permissions…</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <WorkspaceHeader
        user={user}
        onSignOut={() => {
          clearSession();
          setUser(null);
        }}
      />
      <WorkspaceWelcome user={user} latestUpload={latestUpload} />

      {user ? (
        <section className={`workspace-dashboard${canAccessDataIntake ? "" : " single-column"}`}>
          <div id="patient-directory" className="stack section-anchor workspace-primary-column">
            <PatientListPanel refreshKey={refreshKey} />
          </div>
          {canAccessDataIntake ? (
            <aside className="stack workspace-secondary-column">
              <div id="data-intake" className="section-anchor">
                <DataIntakePanel onImported={handleUploaded} />
              </div>
            </aside>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
