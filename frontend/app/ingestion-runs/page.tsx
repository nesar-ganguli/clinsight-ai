import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { IngestionInvestigationPanel } from "@/components/ingestion-investigation-panel";
import { WorkspaceHeader } from "@/components/workspace-header";
import { getCurrentUser, listIngestionBatches } from "@/lib/api";
import { canInvestigateIngestion, TOKEN_STORAGE_KEY } from "@/lib/auth";


export default async function IngestionRunsPage() {
  const token = (await cookies()).get(TOKEN_STORAGE_KEY)?.value;
  if (!token) redirect("/login");

  const user = await getCurrentUser(token);
  if (!canInvestigateIngestion(user)) redirect("/");

  const batches = await listIngestionBatches(token);

  return (
    <main className="shell">
      <WorkspaceHeader user={user} activeSection="ingestion" />
      <div className="page-header">
        <Link href="/" className="back-link">← Back to workspace</Link>
        <span className="eyebrow">Data Quality Operations</span>
        <h1>Ingestion and quarantine review</h1>
        <p>Trace each import, inspect validation failures, and reveal source payloads only when investigation requires it.</p>
        <div className="pill-row">
          <span className="pill">{batches.total} batch{batches.total === 1 ? "" : "es"}</span>
          <span className="pill">{user.role.replaceAll("_", " ")}</span>
          <span className="pill">Read only</span>
        </div>
      </div>
      <IngestionInvestigationPanel batches={batches.items} />
    </main>
  );
}
