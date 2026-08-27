"use client";

import { useState } from "react";

import { ExternalFhirPanel } from "@/components/external-fhir-panel";
import { UploadPanel } from "@/components/upload-panel";
import { UploadResponse } from "@/lib/types";


type IntakePath = "file" | "smart";


export function DataIntakePanel({onImported}: {onImported: (result: UploadResponse) => void}) {
  const [activePath, setActivePath] = useState<IntakePath | null>(null);

  return (
    <section className="panel data-intake-panel">
      <div className="panel-header">
        <div>
          <span className="section-kicker">Operations</span>
          <h2 className="panel-title">Data intake</h2>
          <p className="panel-copy">Choose an import path only when you need to add or refresh patient records.</p>
        </div>
      </div>
      <div className="panel-body data-intake-body">
        <div className="intake-path-list" aria-label="FHIR data intake paths">
          <button
            type="button"
            className={`intake-path-card${activePath === "file" ? " selected" : ""}`}
            aria-expanded={activePath === "file"}
            onClick={() => setActivePath((current) => current === "file" ? null : "file")}
          >
            <span className="intake-path-number" aria-hidden="true">01</span>
            <span>
              <strong>Upload FHIR file</strong>
              <small>Import a local JSON Bundle for one patient.</small>
            </span>
            <span className="intake-path-arrow" aria-hidden="true">{activePath === "file" ? "−" : "+"}</span>
          </button>
          <button
            type="button"
            className={`intake-path-card${activePath === "smart" ? " selected" : ""}`}
            aria-expanded={activePath === "smart"}
            onClick={() => setActivePath((current) => current === "smart" ? null : "smart")}
          >
            <span className="intake-path-number" aria-hidden="true">02</span>
            <span>
              <strong>Import from SMART</strong>
              <small>Search and import from the public FHIR R4 sandbox.</small>
            </span>
            <span className="intake-path-arrow" aria-hidden="true">{activePath === "smart" ? "−" : "+"}</span>
          </button>
        </div>

        {activePath ? (
          <div className="embedded-operation">
            {activePath === "file" ? (
              <UploadPanel onUploaded={onImported} />
            ) : (
              <ExternalFhirPanel onImported={onImported} />
            )}
          </div>
        ) : (
          <div className="intake-guidance">Select an intake path to open its controls.</div>
        )}
      </div>
    </section>
  );
}
