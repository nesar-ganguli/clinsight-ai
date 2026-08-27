"use client";

import { useState } from "react";

import { askPatientQuestion } from "@/lib/api";
import { InsightCitation, PatientChatResponse } from "@/lib/types";

type Props = {
  patientId: number;
  showSourceMetadata: boolean;
};

const suggestedQuestions = [
  "Has this patient had an A1c recently?",
  "Show recent blood pressure readings.",
  "What active medications are documented?",
  "Are there allergies in the chart?",
  "What conditions are currently active?",
];

function formatSourceLabel(citation: InsightCitation) {
  return [
    citation.source_system,
    citation.source_record_id ? `record ${citation.source_record_id}` : null,
    citation.ingestion_batch_id ? `batch ${citation.ingestion_batch_id}` : null,
  ]
    .filter(Boolean)
    .join(" • ");
}

export function PatientChatPanel({ patientId, showSourceMetadata }: Props) {
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const [latestResponse, setLatestResponse] = useState<PatientChatResponse | null>(null);

  async function submitQuestion(nextQuestion = question) {
    const trimmed = nextQuestion.trim();
    if (!trimmed) {
      setError("Ask a chart-review question first.");
      return;
    }

    setPending(true);
    setError(null);
    setLatestResponse(null);
    setSubmittedQuestion(trimmed);
    setQuestion(trimmed);

    try {
      const response = await askPatientQuestion(patientId, trimmed);
      setLatestResponse(response);
      setQuestion("");
    } catch (chatError) {
      setError(chatError instanceof Error ? chatError.message : "Question failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="panel patient-chat-panel">
      <div className="panel-header">
        <div>
          <div className="section-kicker">Grounded chart assistant</div>
          <h2 className="panel-title">Ask about this record</h2>
          <p className="panel-copy">
            Answers are limited to retrieved patient records and include citations. Treatment advice is refused.
          </p>
        </div>
      </div>
      <div className="panel-body patient-chat-body">
        <div className="suggestion-row">
          {suggestedQuestions.map((suggestion) => (
            <button
              key={suggestion}
              className="suggestion-chip"
              type="button"
              onClick={() => submitQuestion(suggestion)}
              disabled={pending}
            >
              {suggestion}
            </button>
          ))}
        </div>
        <div className="chat-input-row">
          <textarea
            className="chat-input"
            value={question}
            placeholder="Ask a chart-review question..."
            rows={3}
            onChange={(event) => setQuestion(event.target.value)}
          />
          <button className="button button-primary" type="button" onClick={() => submitQuestion()} disabled={pending}>
            {pending ? "Asking..." : "Ask"}
          </button>
        </div>

        <div className="chat-result-region" aria-live="polite">
          {pending ? (
            <article className="chat-response-card chat-response-loading" aria-busy="true">
              <div className="chat-question">{submittedQuestion}</div>
              <div className="chat-loading-line">
                <span className="chat-loading-mark" aria-hidden="true" />
                Reviewing the available patient records…
              </div>
            </article>
          ) : error ? (
            <article className="chat-response-card">
              <div className="chat-question">{submittedQuestion}</div>
              <div className="status-banner status-error">{error}</div>
            </article>
          ) : latestResponse ? (
            <article className="chat-response-card">
              <div className="chat-question">{latestResponse.question}</div>
              <p>{latestResponse.answer}</p>
              <div className="pill-row">
                <span className={`badge ${latestResponse.confidence === "low" ? "warning" : "info"}`}>
                  {latestResponse.confidence} confidence
                </span>
                <span className="badge info">{latestResponse.llm_used ? "LLM assisted" : "deterministic"}</span>
                {latestResponse.refused ? <span className="badge warning">advice refused</span> : null}
              </div>
              {latestResponse.citations.length > 0 ? (
                <section className="chat-sources" aria-labelledby={`chat-sources-${patientId}`}>
                  <div className="chat-sources-heading" id={`chat-sources-${patientId}`}>
                    Sources reviewed ({latestResponse.citations.length})
                  </div>
                  <div className="chat-source-list">
                    {latestResponse.citations.map((citation) => {
                      const sourceLabel = showSourceMetadata ? formatSourceLabel(citation) : "";
                      return (
                        <div key={citation.id} className="chat-source-card">
                          <div className="chat-source-header">
                            <span className="badge info">{citation.resource_type}</span>
                            <strong>{citation.label}</strong>
                          </div>
                          <p>{citation.excerpt}</p>
                          <div className="chat-source-record">
                            Record #{citation.record_id}
                            {citation.date ? ` • ${citation.date}` : ""}
                          </div>
                          {sourceLabel ? <div className="chat-source-provenance">{sourceLabel}</div> : null}
                        </div>
                      );
                    })}
                  </div>
                </section>
              ) : null}
              {latestResponse.safety_notes.length > 0 ? (
                <div className="meta-line">{latestResponse.safety_notes.join(" ")}</div>
              ) : null}
            </article>
          ) : null}
        </div>
      </div>
    </section>
  );
}
