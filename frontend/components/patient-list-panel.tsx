"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listPatients } from "@/lib/api";
import { PatientSummary } from "@/lib/types";

type Props = {
  refreshKey: number;
};

export function PatientListPanel({ refreshKey }: Props) {
  const [search, setSearch] = useState("");
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadPatients() {
      setLoading(true);
      setError(null);

      try {
        const result = await listPatients(search.trim() || undefined);
        if (!active) {
          return;
        }
        setPatients(result.items);
        setTotal(result.total);
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Unable to load patients");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadPatients();

    return () => {
      active = false;
    };
  }, [search]);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Patient Directory</h2>
          <p className="panel-copy">
            Search imported patient records and jump directly into the longitudinal chart view.
          </p>
        </div>
        <div className="badge info">{total} patient{total === 1 ? "" : "s"}</div>
      </div>
      <div className="panel-body">
        <div className="search-row">
          <input
            className="search-input"
            placeholder="Search by patient name or FHIR ID"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        {loading ? <div className="loading">Loading patient directory...</div> : null}
        {error ? <div className="status-banner status-error">{error}</div> : null}

        {!loading && !error && patients.length === 0 ? (
          <div className="empty-state">No patients found yet. Upload a FHIR bundle to populate the workspace.</div>
        ) : null}

        <div className="list">
          {patients.map((patient) => (
            <Link key={patient.id} href={`/patients/${patient.id}`} className="patient-card">
              <div>
                <p className="patient-name">{patient.full_name || "Unnamed patient"}</p>
                <p className="patient-meta">FHIR ID: {patient.fhir_patient_id || "Unavailable"}</p>
              </div>
              <div className="pill-row">
                <span className="pill">{patient.gender || "Gender unknown"}</span>
                <span className="pill">{patient.birth_date || "DOB unavailable"}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
