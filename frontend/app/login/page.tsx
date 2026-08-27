"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { listDemoAuthAccounts, login } from "@/lib/api";
import { saveSession } from "@/lib/auth";
import { DemoAuthAccount, UserRole } from "@/lib/types";

const ROLE_GUIDANCE: Record<UserRole, {label: string; focus: string; capabilities: string[]}> = {
  admin: {
    label: "Administrator",
    focus: "Full clinical review and data-operations access.",
    capabilities: ["Patient charts and clinical insights", "FHIR data intake and quarantine review", "Audit trail"],
  },
  clinician: {
    label: "Clinician",
    focus: "Clinical chart review with grounded summaries.",
    capabilities: ["Patient charts and timelines", "Grounded summaries and inconsistencies", "Chart-grounded questions"],
  },
  care_coordinator: {
    label: "Care coordinator",
    focus: "Patient follow-up and care-gap review.",
    capabilities: ["Patient charts and timelines", "Care-gap suggestions", "Chart-grounded questions"],
  },
  data_reviewer: {
    label: "Data reviewer",
    focus: "Data quality, provenance, and ingestion operations.",
    capabilities: ["Patient quality and source metadata", "FHIR data intake and quarantine review", "Audit trail"],
  },
};

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("clinician");
  const [accounts, setAccounts] = useState<DemoAuthAccount[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [password, setPassword] = useState("clinsight-demo");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const selectedAccount = accounts.find((account) => account.username === username) ?? accounts[0] ?? null;
  const selectedGuidance = selectedAccount ? ROLE_GUIDANCE[selectedAccount.role] : null;

  useEffect(() => {
    let active = true;
    void listDemoAuthAccounts()
      .then((response) => {
        if (!active) return;
        setAccounts(response.items);
        setUsername((current) => (
          response.items.some((account) => account.username === current)
            ? current
            : response.items[0]?.username || current
        ));
      })
      .catch((loadError) => {
        if (active) {
          setAccountsError(loadError instanceof Error ? loadError.message : "Unable to load demo accounts");
        }
      })
      .finally(() => {
        if (active) setAccountsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);

    try {
      const result = await login(username, password);
      saveSession(result.access_token, result.user);
      router.push("/");
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Unable to sign in");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="shell auth-shell">
      <section className="panel auth-panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">ClinSight AI</span>
            <h1 className="panel-title">Sign in</h1>
            <p className="panel-copy">Choose a demo account based on the workflow you want to explore.</p>
          </div>
        </div>
        <form className="panel-body auth-form" onSubmit={handleSubmit}>
          <fieldset className="role-picker">
            <legend className="label">Demo account</legend>
            {accountsLoading ? <div className="loading">Loading active demo accounts…</div> : null}
            {accountsError ? <div className="status-banner status-error">{accountsError}</div> : null}
            <div className="role-picker-grid">
              {accounts.map((account) => {
                const guidance = ROLE_GUIDANCE[account.role];
                return (
                <button
                  key={account.username}
                  className={`role-option${username === account.username ? " selected" : ""}`}
                  type="button"
                  aria-pressed={username === account.username}
                  onClick={() => setUsername(account.username)}
                >
                  <strong>{guidance.label}</strong>
                  <small>{account.full_name || account.username}</small>
                </button>
                );
              })}
            </div>
          </fieldset>

          {selectedAccount && selectedGuidance ? <section className="selected-role-summary" aria-live="polite">
            <span className="section-kicker">Selected access</span>
            <h2>{selectedGuidance.label}</h2>
            <p>{selectedGuidance.focus}</p>
            <ul>
              {selectedGuidance.capabilities.map((capability) => (
                <li key={capability}><span aria-hidden="true">✓</span>{capability}</li>
              ))}
            </ul>
          </section> : null}

          <label className="label" htmlFor="password">Shared demo password</label>
          <input
            id="password"
            className="search-input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />

          {error ? <div className="status-banner status-error">{error}</div> : null}

          <button className="button button-primary" type="submit" disabled={pending || accountsLoading || !selectedAccount}>
            {pending ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
