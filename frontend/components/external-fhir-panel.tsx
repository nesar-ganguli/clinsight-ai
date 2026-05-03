"use client";

import { useState } from "react";

import { importSmartFhirPatient, searchSmartFhirPatients } from "@/lib/api";
import { ExternalFhirPatientSummary, UploadResponse } from "@/lib/types";

type Props = {
  onImported: (result: UploadResponse) => void;
};

export function ExternalFhirPanel({ onImported }: Props) {
  const [search, setSearch] = useState("");
  const [patients, setPatients] = useState<ExternalFhirPatientSummary[]>([]);
  const [sourceLabel, setSourceLabel] = useState("SMART Health IT R4 Sandbox");
  const [pending, setPending] = useState(false);
  const [importingId, setImportingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [latestImport, setLatestImport] = useState<UploadResponse | null>(null);

  async function handleSearch() {
    setPending(true);
    setError(null);
    setLatestImport(null);

    try {
      const result = await searchSmartFhirPatients(search.trim() || undefined);
      setPatients(result.items);
      setSourceLabel(result.source_system);
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "SMART FHIR search failed");
    } finally {
      setPending(false);
    }
  }

  async function handleImport(patientId: string) {
    setImportingId(patientId);
    setError(null);

    try {
      const result = await importSmartFhirPatient(patientId);
      setLatestImport(result);
      onImported(result);
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "SMART FHIR import failed");
    } finally {
      setImportingId(null);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Import From SMART Health IT</h2>
          <p className="panel-copy">
            Search the public HL7 FHIR R4 sandbox, then import a selected patient through the existing FHIR pipeline.
          </p>
        </div>
        <span className="badge info">FHIR R4</span>
      </div>
      <div className="panel-body">
        <label className="label" htmlFor="smart-fhir-search">
          Patient search
        </label>
        <div className="search-row">
          <input
            id="smart-fhir-search"
            className="search-input"
            value={search}
            placeholder="Name"
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleSearch();
              }
            }}
          />
          <button className="button button-primary" type="button" onClick={handleSearch} disabled={pending}>
            {pending ? "Searching..." : "Search"}
          </button>
        </div>

        {error ? <div className="status-banner status-error">{error}</div> : null}

        {latestImport ? (
          <div className="status-banner status-success">
            <strong>{latestImport.import_mode === "created" ? "Patient imported." : "Patient updated."}</strong>{" "}
            Record #{latestImport.patient_id} is ready for review.
          </div>
        ) : null}

        <div className="list">
          {patients.map((patient) => (
            <article key={patient.id} className="patient-card">
              <div>
                <div className="patient-name">{patient.full_name || "Unnamed patient"}</div>
                <div className="patient-meta">
                  {patient.gender || "unknown"} · {patient.birth_date || "birth date unavailable"} · {sourceLabel}
                </div>
                <div className="patient-meta">FHIR ID: {patient.id}</div>
              </div>
              <button
                className="button button-secondary"
                type="button"
                onClick={() => handleImport(patient.id)}
                disabled={importingId === patient.id}
              >
                {importingId === patient.id ? "Importing..." : "Import"}
              </button>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
