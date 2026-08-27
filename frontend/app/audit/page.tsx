import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser, listAuditLogs } from "@/lib/api";
import { canViewAuditLogs, TOKEN_STORAGE_KEY } from "@/lib/auth";
import { AuditLog } from "@/lib/types";
import { WorkspaceHeader } from "@/components/workspace-header";


function formatDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}


type AuditUserGroup = {
  key: string;
  displayName: string;
  role: string | null;
  events: AuditLog[];
};


function groupAuditEvents(events: AuditLog[]): AuditUserGroup[] {
  const groups = new Map<string, AuditUserGroup>();

  for (const event of events) {
    const key = event.user_id !== null ? `user-${event.user_id}` : `system-${event.username || "system"}`;
    const existing = groups.get(key);
    if (existing) {
      existing.events.push(event);
      continue;
    }

    groups.set(key, {
      key,
      displayName: event.username || "System",
      role: event.role,
      events: [event],
    });
  }

  return Array.from(groups.values()).sort((left, right) => {
    if (left.displayName === "System") return 1;
    if (right.displayName === "System") return -1;
    return left.displayName.localeCompare(right.displayName);
  });
}


export default async function AuditPage() {
  const token = (await cookies()).get(TOKEN_STORAGE_KEY)?.value;
  if (!token) {
    redirect("/login");
  }

  const user = await getCurrentUser(token);
  if (!canViewAuditLogs(user)) {
    redirect("/");
  }

  const auditLogs = await listAuditLogs(token);
  const userGroups = groupAuditEvents(auditLogs.items);

  return (
    <main className="shell">
      <WorkspaceHeader user={user} activeSection="audit" />
      <div className="page-header">
        <Link href="/" className="back-link">
          ← Back to workspace
        </Link>
        <span className="eyebrow">Audit Trail</span>
        <h1>Healthcare traceability log</h1>
        <p>Review recent login, patient access, AI insight, ingestion, and transformation events grouped by actor.</p>
        <div className="pill-row">
          <span className="pill">{auditLogs.total} event{auditLogs.total === 1 ? "" : "s"}</span>
          <span className="pill">{userGroups.length} actor{userGroups.length === 1 ? "" : "s"} in this page</span>
          <span className="pill">{user.role.replaceAll("_", " ")}</span>
        </div>
      </div>

      <section className="panel audit-log-panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Recent events by user</h2>
            <p className="panel-copy">Groups are alphabetical; events inside each group remain newest first. This view contains the latest {auditLogs.items.length} records.</p>
          </div>
        </div>
        <div className="panel-body">
          {userGroups.length === 0 ? <div className="empty-state">No audit events are available.</div> : (
            <div className="audit-user-groups">
              {userGroups.map((group) => (
                <section key={group.key} className="audit-user-group">
                  <div className="audit-user-header">
                    <div>
                      <h3>{group.displayName}</h3>
                      <div className="meta-line">{group.role ? group.role.replaceAll("_", " ") : "automated or unauthenticated actor"}</div>
                    </div>
                    <span className="pill">{group.events.length} event{group.events.length === 1 ? "" : "s"}</span>
                  </div>
                  <div className="audit-event-list">
                    {group.events.map((event) => (
                      <article key={event.id} className="timeline-card">
                        <div className="timeline-kicker">{event.action.replaceAll("_", " ")}</div>
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
                </section>
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
