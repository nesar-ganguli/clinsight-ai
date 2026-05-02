"use client";

import { useState } from "react";

import { uploadBundle } from "@/lib/api";
import { UploadResponse } from "@/lib/types";

type Props = {
  onUploaded: (result: UploadResponse) => void;
};

export function UploadPanel({ onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  async function handleUpload() {
    if (!file) {
      setError("Choose a FHIR Bundle JSON file before importing.");
      return;
    }

    setPending(true);
    setError(null);

    try {
      const uploadResult = await uploadBundle(file);
      setResult(uploadResult);
      onUploaded(uploadResult);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Import FHIR Bundle</h2>
          <p className="panel-copy">
            Bring in longitudinal patient records from a FHIR bundle and refresh the patient workspace instantly.
          </p>
        </div>
      </div>
      <div className="panel-body">
        <label className="label" htmlFor="bundle-file">
          FHIR bundle JSON
        </label>
        <input
          id="bundle-file"
          className="file-input"
          type="file"
          accept=".json,application/json"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />

        <div className="button-row">
          <button className="button button-primary" onClick={handleUpload} disabled={pending}>
            {pending ? "Importing..." : "Upload Bundle"}
          </button>
        </div>

        {error ? <div className="status-banner status-error">{error}</div> : null}

        {result ? (
          <div className="status-banner status-success">
            <strong>{result.import_mode === "created" ? "Patient created." : "Patient updated."}</strong>{" "}
            Record #{result.patient_id} is ready for review.
            <div className="metric-strip">
              {Object.entries(result.resource_counts).map(([resource, count]) => (
                <div key={resource} className="metric">
                  <div className="metric-label">{resource}</div>
                  <div className="metric-value">{count}</div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
