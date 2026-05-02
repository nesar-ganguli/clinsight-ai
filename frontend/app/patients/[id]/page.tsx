import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser, getPatient, getPatientAiInsights, getQualityAlerts } from "@/lib/api";
import { canViewCareGaps, canViewInsights, canViewQuality, canViewSourceMetadata, TOKEN_STORAGE_KEY } from "@/lib/auth";
import { buildTimeline } from "@/lib/timeline";
import { InsightCitation, PatientAiInsightsResponse, QualityAlertsResponse } from "@/lib/types";

function formatDate(value: string | null) {
  if (!value) {
    return "Date unavailable";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function formatSourceLabel(citation: InsightCitation) {
  return [
    citation.source_system,
    citation.source_record_id ? `record ${citation.source_record_id}` : null,
    citation.ingestion_batch_id ? `batch ${citation.ingestion_batch_id}` : null,
  ]
    .filter(Boolean)
    .join(" • ");
}

export default async function PatientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const token = (await cookies()).get(TOKEN_STORAGE_KEY)?.value;
  if (!token) {
    redirect("/login");
  }

  const user = await getCurrentUser(token);
  const [patient, quality, insights] = await Promise.all([
    getPatient(id, token),
    canViewQuality(user.role)
      ? getQualityAlerts(id, token)
      : Promise.resolve<QualityAlertsResponse>({patient_id: Number(id), alerts: []}),
    canViewInsights(user.role) || canViewCareGaps(user.role)
      ? getPatientAiInsights(id, token)
      : Promise.resolve<PatientAiInsightsResponse>({
          patient_id: Number(id),
          generated_by: "ClinSight grounded insight rules v1",
          disclaimer: "AI-assisted chart review. Verify all findings against the source record before clinical use.",
          summary_sections: [],
          inconsistencies: [],
          care_gaps: [],
          citations: [],
          evaluation: {
            grounded_claims: 0,
            unsupported_claims: 0,
            unresolved_citations: 0,
            source_coverage: 0,
            hallucination_risk: "low",
            checks: [],
          },
        }),
  ]);

  const timeline = buildTimeline(patient);
  const citationsById = new Map(insights.citations.map((citation) => [citation.id, citation]));
  const displayedAllergies = patient.allergies.slice(0, 3);
  const hiddenAllergyCount = Math.max(patient.allergies.length - displayedAllergies.length, 0);

  function renderCitations(citationIds: string[]) {
    const citations = citationIds
      .map((citationId) => citationsById.get(citationId))
      .filter((citation): citation is InsightCitation => Boolean(citation));

    if (citations.length === 0) {
      return null;
    }

    return (
      <div className="citation-row" aria-label="Source records">
        {citations.map((citation) => {
          const sourceLabel = canViewSourceMetadata(user.role) ? formatSourceLabel(citation) : "";
          return (
            <span
              key={citation.id}
              className="citation-chip"
              title={[citation.excerpt, sourceLabel].filter(Boolean).join(" | ")}
            >
              <span>{citation.resource_type} #{citation.record_id}</span>
              {sourceLabel ? <span>{sourceLabel}</span> : null}
            </span>
          );
        })}
      </div>
    );
  }

  return (
    <main className="shell">
      <div className="page-header">
        <Link href="/" className="back-link">
          ← Back to workspace
        </Link>
        <span className="eyebrow">Patient Chart</span>
        <h1>{patient.full_name || "Unnamed patient"}</h1>
        <p>
          FHIR ID {patient.fhir_patient_id || "Unavailable"} • {patient.gender || "Gender unknown"} •{" "}
          {patient.birth_date || "Birth date unavailable"}
        </p>
        {canViewSourceMetadata(user.role) ? (
          <p>
            Source {patient.source_system || "Unavailable"} • Record {patient.source_record_id || "Unavailable"} • Batch{" "}
            {patient.ingestion_batch_id || "Unavailable"}
          </p>
        ) : null}
        <div className="pill-row">
          <span className="pill">{user.role.replaceAll("_", " ")}</span>
          <span className="pill">{patient.conditions.length} conditions</span>
          <span className="pill">{patient.observations.length} observations</span>
          <span className="pill">{patient.encounters.length} encounters</span>
          <span className="pill">{quality.alerts.length} quality alerts</span>
        </div>
        <div className="allergy-strip" aria-label="Patient allergies">
          <span className="allergy-label">Allergies</span>
          {displayedAllergies.length > 0 ? (
            <>
              {displayedAllergies.map((allergy) => (
                <span key={allergy.id} className={`allergy-chip criticality-${allergy.criticality || "unknown"}`}>
                  {allergy.allergy_name || "Unnamed allergy"}
                  {allergy.criticality ? <span>{allergy.criticality}</span> : null}
                </span>
              ))}
              {hiddenAllergyCount > 0 ? (
                <span className="allergy-more">
                  <button className="allergy-chip criticality-unknown" type="button">
                    +{hiddenAllergyCount} more
                  </button>
                  <span className="allergy-popover" role="tooltip">
                    {patient.allergies.slice(3).map((allergy) => (
                      <span key={allergy.id} className="allergy-popover-item">
                        <strong>{allergy.allergy_name || "Unnamed allergy"}</strong>
                        {allergy.criticality ? <span>{allergy.criticality}</span> : null}
                      </span>
                    ))}
                  </span>
                </span>
              ) : null}
            </>
          ) : (
            <span className="allergy-chip allergy-none">No allergies documented</span>
          )}
        </div>
      </div>

      <section className="detail-grid">
        <div className="stack">
          <section className="panel summary-card">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Grounded AI summary</div>
                <h2 className="panel-title">Patient snapshot</h2>
                <p className="panel-copy">{insights.disclaimer}</p>
              </div>
            </div>
            <div className="panel-body insight-stack">
              {!canViewInsights(user.role) ? (
                <div className="empty-state">Your role does not include grounded AI summary access.</div>
              ) : null}
              {insights.summary_sections.map((section) => (
                <section key={section.title} className="insight-section">
                  <h3>{section.title}</h3>
                  <div className="claim-list">
                    {section.claims.map((claim) => (
                      <article key={claim.id} className="claim-card">
                        <p>{claim.text}</p>
                        {renderCitations(claim.citation_ids)}
                      </article>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Longitudinal view</div>
                <h2 className="panel-title">Chart timeline</h2>
                <p className="panel-copy">Key patient events across encounters, conditions, observations, medication activity, and allergies.</p>
              </div>
            </div>
            <div className="panel-body">
              <div className="timeline">
                {timeline.length === 0 ? (
                  <div className="empty-state">No timeline events available for this patient yet.</div>
                ) : (
                  timeline.map((item) => (
                    <article key={item.id} className="timeline-card">
                      <div className="timeline-kicker">{item.type}</div>
                      <strong>{item.label}</strong>
                      <div>{item.detail}</div>
                      <div className="meta-line">{formatDate(item.date)}</div>
                      {item.meta ? <div className="meta-line">{item.meta}</div> : null}
                    </article>
                  ))
                )}
              </div>
            </div>
          </section>
        </div>

        <div className="stack">
          <section className="panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Care intelligence</div>
                <h2 className="panel-title">Care gap suggestions</h2>
              </div>
            </div>
            <div className="panel-body">
              <div className="list">
                {!canViewCareGaps(user.role) ? (
                  <div className="empty-state">Care gap suggestions are available to care coordinators and admins.</div>
                ) : null}
                {canViewCareGaps(user.role) ? insights.care_gaps.map((gap) => (
                  <article key={gap.code} className={`care-gap-card priority-${gap.priority}`}>
                    <div className="alert-header">
                      <strong>{gap.title}</strong>
                      <span className={`badge priority-${gap.priority}`}>{gap.priority}</span>
                    </div>
                    <p>{gap.recommendation}</p>
                    <div className="meta-line">{gap.rationale}</div>
                    {renderCitations(gap.citation_ids)}
                  </article>
                )) : null}
              </div>
            </div>
          </section>

          {canViewInsights(user.role) ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Consistency engine</div>
                <h2 className="panel-title">Chart inconsistency detection</h2>
              </div>
            </div>
            <div className="panel-body">
              <div className="list">
                {insights.inconsistencies.map((finding) => (
                  <article key={finding.code} className={`alert-card ${finding.severity}`}>
                    <div className="alert-header">
                      <strong>{finding.title}</strong>
                      <span className={`badge ${finding.severity}`}>{finding.severity}</span>
                    </div>
                    <p>{finding.explanation}</p>
                    {renderCitations(finding.citation_ids)}
                  </article>
                ))}
              </div>
            </div>
          </section>
          ) : null}

          {canViewInsights(user.role) ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Evaluation framework</div>
                <h2 className="panel-title">Grounding checks</h2>
              </div>
            </div>
            <div className="panel-body">
              <div className="evaluation-grid">
                <div className="mini-card">
                  <div className="metric-label">Grounded claims</div>
                  <div className="metric-value">{insights.evaluation.grounded_claims}</div>
                </div>
                <div className="mini-card">
                  <div className="metric-label">Unsupported claims</div>
                  <div className="metric-value">{insights.evaluation.unsupported_claims}</div>
                </div>
                <div className="mini-card">
                  <div className="metric-label">Unresolved citations</div>
                  <div className="metric-value">{insights.evaluation.unresolved_citations}</div>
                </div>
                <div className="mini-card">
                  <div className="metric-label">Hallucination risk</div>
                  <div className={`risk-value risk-${insights.evaluation.hallucination_risk}`}>
                    {insights.evaluation.hallucination_risk}
                  </div>
                </div>
              </div>
              <div className="check-list">
                {insights.evaluation.checks.map((check) => (
                  <div key={check} className="check-item">{check}</div>
                ))}
              </div>
            </div>
          </section>
          ) : null}

          {canViewQuality(user.role) ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Quality dashboard</div>
                <h2 className="panel-title">Chart review alerts</h2>
              </div>
            </div>
            <div className="panel-body">
              <div className="list">
                {quality.alerts.length === 0 ? (
                  <div className="empty-state">No quality alerts for this patient. The record is currently complete enough for review.</div>
                ) : (
                  quality.alerts.map((alert) => (
                    <article key={`${alert.code}-${alert.field}-${alert.message}`} className={`alert-card ${alert.severity}`}>
                      <div className="alert-header">
                        <strong>{alert.code.replaceAll("_", " ")}</strong>
                        <span className={`badge ${alert.severity}`}>{alert.severity}</span>
                      </div>
                      <div className="meta-line">{alert.category} • {alert.field}</div>
                      <p>{alert.message}</p>
                    </article>
                  ))
                )}
              </div>
            </div>
          </section>
          ) : null}

          <section className="panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Resource inventory</div>
                <h2 className="panel-title">Patient record contents</h2>
              </div>
            </div>
            <div className="panel-body">
              <div className="resource-grid">
                <div className="mini-card">
                  <div className="metric-label">Conditions</div>
                  <div className="metric-value">{patient.conditions.length}</div>
                </div>
                <div className="mini-card">
                  <div className="metric-label">Observations</div>
                  <div className="metric-value">{patient.observations.length}</div>
                </div>
                <div className="mini-card">
                  <div className="metric-label">Encounters</div>
                  <div className="metric-value">{patient.encounters.length}</div>
                </div>
                <div className="mini-card">
                  <div className="metric-label">Medication requests</div>
                  <div className="metric-value">{patient.medication_requests.length}</div>
                </div>
                <div className="mini-card">
                  <div className="metric-label">Allergies</div>
                  <div className="metric-value">{patient.allergies.length}</div>
                </div>
                <div className="mini-card">
                  <div className="metric-label">FHIR patient ID</div>
                  <div className="metric-value" style={{ fontSize: "1rem" }}>
                    {patient.fhir_patient_id || "Unavailable"}
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
