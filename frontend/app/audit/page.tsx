import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser, listAuditLogs } from "@/lib/api";
import { canViewAuditLogs, TOKEN_STORAGE_KEY } from "@/lib/auth";


function formatDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}


export default async function AuditPage() {
  const token = (await cookies()).get(TOKEN_STORAGE_KEY)?.value;
  if (!token) {
    redirect("/login");
  }

  const user = await getCurrentUser(token);
  if (!canViewAuditLogs(user.role)) {
    redirect("/");
  }

  const auditLogs = await listAuditLogs(token);

  return (
    <main className="shell">
      <div className="page-header">
        <Link href="/" className="back-link">
          ← Back to workspace
        </Link>
        <span className="eyebrow">Audit Trail</span>
        <h1>Healthcare traceability log</h1>
        <p>Review login, patient access, AI insight, ingestion, and transformation events.</p>
        <div className="pill-row">
          <span className="pill">{auditLogs.total} event{auditLogs.total === 1 ? "" : "s"}</span>
          <span className="pill">{user.role.replaceAll("_", " ")}</span>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Recent audit events</h2>
            <p className="panel-copy">Use patient resource events to answer who viewed a record and when.</p>
          </div>
        </div>
        <div className="panel-body">
          <div className="list">
            {auditLogs.items.map((event) => (
              <article key={event.id} className="timeline-card">
                <div className="timeline-kicker">{event.action.replaceAll("_", " ")}</div>
                <strong>{event.username || "system"} {event.role ? `(${event.role.replaceAll("_", " ")})` : ""}</strong>
                <div className="meta-line">{formatDate(event.event_timestamp)}</div>
                <div className="meta-line">
                  {event.resource_type || "resource"} {event.resource_id || "unavailable"}
                  {event.patient_id ? ` • patient ${event.patient_id}` : ""}
                </div>
                {Object.keys(event.metadata).length > 0 ? (
                  <pre className="audit-metadata">{JSON.stringify(event.metadata, null, 2)}</pre>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
