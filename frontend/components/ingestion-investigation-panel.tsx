"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { getQuarantinePayload, listQuarantineRecords } from "@/lib/api";
import { IngestionBatch, QuarantineRecordSummary } from "@/lib/types";


function formatDate(value: string | null) {
  if (!value) return "Not completed";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}


export function IngestionInvestigationPanel({batches}: {batches: IngestionBatch[]}) {
  const preferredBatch = batches.find((batch) => batch.quarantine_count > 0) ?? batches[0] ?? null;
  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(preferredBatch?.id ?? null);
  const [batchSearch, setBatchSearch] = useState("");
  const [onlyQuarantined, setOnlyQuarantined] = useState(false);
  const [resourceType, setResourceType] = useState("");
  const [errorCode, setErrorCode] = useState("");
  const [recordSearch, setRecordSearch] = useState("");
  const [records, setRecords] = useState<QuarantineRecordSummary[]>([]);
  const [recordTotal, setRecordTotal] = useState(0);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [openPayloadId, setOpenPayloadId] = useState<number | null>(null);
  const [payloads, setPayloads] = useState<Record<number, unknown>>({});
  const [payloadLoadingId, setPayloadLoadingId] = useState<number | null>(null);
  const [payloadError, setPayloadError] = useState<string | null>(null);

  const selectedBatch = batches.find((batch) => batch.id === selectedBatchId) ?? null;
  const filteredBatches = useMemo(() => {
    const normalized = batchSearch.trim().toLowerCase();
    return batches.filter((batch) => {
      if (onlyQuarantined && batch.quarantine_count === 0) return false;
      if (!normalized) return true;
      return [batch.filename, batch.source_system_name, batch.status, String(batch.id)]
        .some((value) => value?.toLowerCase().includes(normalized));
    });
  }, [batchSearch, batches, onlyQuarantined]);

  async function loadRecords(batchId: number) {
    setLoadingRecords(true);
    setRecordsError(null);
    setOpenPayloadId(null);
    setPayloadError(null);
    try {
      const response = await listQuarantineRecords(batchId, {
        resourceType: resourceType.trim(),
        errorCode: errorCode.trim(),
        search: recordSearch.trim(),
      });
      setRecords(response.items);
      setRecordTotal(response.total);
    } catch (error) {
      setRecords([]);
      setRecordTotal(0);
      setRecordsError(error instanceof Error ? error.message : "Unable to load quarantine records");
    } finally {
      setLoadingRecords(false);
    }
  }

  useEffect(() => {
    if (selectedBatchId !== null) void loadRecords(selectedBatchId);
    // Filters are applied explicitly by the form; batch selection always refreshes the detail panel.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBatchId]);

  function applyRecordFilters(event: FormEvent) {
    event.preventDefault();
    if (selectedBatchId !== null) void loadRecords(selectedBatchId);
  }

  async function togglePayload(recordId: number) {
    setPayloadError(null);
    if (openPayloadId === recordId) {
      setOpenPayloadId(null);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(payloads, recordId)) {
      setOpenPayloadId(recordId);
      return;
    }

    setPayloadLoadingId(recordId);
    try {
      const response = await getQuarantinePayload(recordId);
      setPayloads((current) => ({...current, [recordId]: response.raw_payload}));
      setOpenPayloadId(recordId);
    } catch (error) {
      setPayloadError(error instanceof Error ? error.message : "Unable to load raw payload");
    } finally {
      setPayloadLoadingId(null);
    }
  }

  if (batches.length === 0) {
    return <div className="empty-state">No ingestion batches have been recorded yet.</div>;
  }

  return (
    <section className="ingestion-review-grid">
      <aside className="panel ingestion-batch-panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Ingestion batches</h2>
            <p className="panel-copy">Latest {batches.length} batches, newest first.</p>
          </div>
        </div>
        <div className="panel-body ingestion-batch-body">
          <input
            className="search-input"
            type="search"
            placeholder="Filename, source, status, or batch ID"
            aria-label="Filter ingestion batches"
            value={batchSearch}
            onChange={(event) => setBatchSearch(event.target.value)}
          />
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={onlyQuarantined}
              onChange={(event) => setOnlyQuarantined(event.target.checked)}
            />
            Show only batches with quarantine rows
          </label>
          <div className="ingestion-batch-list">
            {filteredBatches.length === 0 ? (
              <div className="empty-state">No batches match this filter.</div>
            ) : filteredBatches.map((batch) => (
              <button
                key={batch.id}
                type="button"
                className={`ingestion-batch-card${batch.id === selectedBatchId ? " selected" : ""}`}
                onClick={() => setSelectedBatchId(batch.id)}
              >
                <span className="ingestion-batch-heading">
                  <strong>{batch.filename || `${batch.ingestion_type} batch`}</strong>
                  <span className={`badge batch-status-${batch.status}`}>{batch.status.replaceAll("_", " ")}</span>
                </span>
                <span className="meta-line">Batch #{batch.id} • {batch.source_system_name}</span>
                <span className="batch-counts">
                  <span>{batch.accepted_count} accepted</span>
                  <span>{batch.rejected_count} rejected</span>
                  <span>{batch.quarantine_count} quarantined</span>
                </span>
                <span className="meta-line">{formatDate(batch.started_at)}</span>
              </button>
            ))}
          </div>
        </div>
      </aside>

      <section className="panel quarantine-panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Quarantine investigation</h2>
            <p className="panel-copy">
              {selectedBatch
                ? `Batch #${selectedBatch.id} from ${selectedBatch.source_system_name}`
                : "Select an ingestion batch to investigate."}
            </p>
          </div>
          {selectedBatch ? <span className="pill">{selectedBatch.quarantine_count} quarantined</span> : null}
        </div>
        <div className="panel-body quarantine-body">
          {selectedBatch ? (
            <>
              <div className="batch-summary-grid">
                <div className="metric"><div className="metric-label">Received</div><div className="metric-value">{selectedBatch.record_count}</div></div>
                <div className="metric"><div className="metric-label">Accepted</div><div className="metric-value">{selectedBatch.accepted_count}</div></div>
                <div className="metric"><div className="metric-label">Rejected</div><div className="metric-value">{selectedBatch.rejected_count}</div></div>
              </div>
              {selectedBatch.error_message ? <div className="error-message">{selectedBatch.error_message}</div> : null}
              <form className="quarantine-filters" onSubmit={applyRecordFilters}>
                <input className="search-input" placeholder="Resource type" aria-label="Resource type" value={resourceType} onChange={(event) => setResourceType(event.target.value)} />
                <input className="search-input" placeholder="Error code" aria-label="Error code" value={errorCode} onChange={(event) => setErrorCode(event.target.value)} />
                <input className="search-input" placeholder="Record ID or error message" aria-label="Quarantine search" value={recordSearch} onChange={(event) => setRecordSearch(event.target.value)} />
                <button className="button primary" type="submit" disabled={loadingRecords}>Apply filters</button>
              </form>
              <div className="meta-line">{recordTotal} matching quarantine row{recordTotal === 1 ? "" : "s"}</div>
              {recordsError ? <div className="error-message">{recordsError}</div> : null}
              {payloadError ? <div className="error-message">{payloadError}</div> : null}
              {loadingRecords ? (
                <div className="empty-state">Loading quarantine records…</div>
              ) : records.length === 0 ? (
                <div className="empty-state">No quarantine records match this batch and filter.</div>
              ) : (
                <div className="quarantine-list">
                  {records.map((record) => (
                    <article key={record.id} className="quarantine-card">
                      <div className="quarantine-card-header">
                        <div>
                          <div className="section-kicker">{record.error_code.replaceAll("_", " ")}</div>
                          <h3>{record.resource_type} {record.source_record_id ? `• ${record.source_record_id}` : ""}</h3>
                        </div>
                        <span className="meta-line">#{record.id}</span>
                      </div>
                      <p>{record.error_message}</p>
                      <div className="meta-line">Quarantined {formatDate(record.created_at)}</div>
                      <button
                        className="button secondary"
                        type="button"
                        disabled={payloadLoadingId === record.id}
                        onClick={() => void togglePayload(record.id)}
                      >
                        {payloadLoadingId === record.id
                          ? "Loading payload…"
                          : openPayloadId === record.id
                            ? "Hide raw payload"
                            : "View raw payload (audited)"}
                      </button>
                      {openPayloadId === record.id ? (
                        <pre className="raw-payload">{JSON.stringify(payloads[record.id], null, 2)}</pre>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </>
          ) : <div className="empty-state">Select a batch from the left.</div>}
        </div>
      </section>
    </section>
  );
}
