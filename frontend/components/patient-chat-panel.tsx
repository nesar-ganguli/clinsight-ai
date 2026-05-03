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
  const [responses, setResponses] = useState<PatientChatResponse[]>([]);

  async function submitQuestion(nextQuestion = question) {
    const trimmed = nextQuestion.trim();
    if (!trimmed) {
      setError("Ask a chart-review question first.");
      return;
    }

    setPending(true);
    setError(null);
    setQuestion(trimmed);

    try {
      const response = await askPatientQuestion(patientId, trimmed);
      setResponses((current) => [response, ...current].slice(0, 5));
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

        {error ? <div className="status-banner status-error">{error}</div> : null}

        <div className="chat-response-list">
          {responses.map((response) => (
            <article key={`${response.question}-${response.generated_by}`} className="chat-response-card">
              <div className="chat-question">{response.question}</div>
              <p>{response.answer}</p>
              <div className="pill-row">
                <span className={`badge ${response.confidence === "low" ? "warning" : "info"}`}>
                  {response.confidence} confidence
                </span>
                <span className="badge info">{response.llm_used ? "LLM assisted" : "deterministic"}</span>
                {response.refused ? <span className="badge warning">advice refused</span> : null}
              </div>
              {response.citations.length > 0 ? (
                <div className="citation-row" aria-label="Retrieved source records">
                  {response.citations.map((citation) => {
                    const sourceLabel = showSourceMetadata ? formatSourceLabel(citation) : "";
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
              ) : null}
              {response.safety_notes.length > 0 ? (
                <div className="meta-line">{response.safety_notes.join(" ")}</div>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
