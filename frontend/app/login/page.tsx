"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { login } from "@/lib/api";
import { saveSession } from "@/lib/auth";

const DEMO_ACCOUNTS = [
  {username: "admin", label: "Admin"},
  {username: "clinician", label: "Clinician"},
  {username: "care", label: "Care coordinator"},
  {username: "reviewer", label: "Data reviewer"},
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("clinician");
  const [password, setPassword] = useState("clinsight-demo");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

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
            <p className="panel-copy">Use a demo role to review the protected clinical workspace.</p>
          </div>
        </div>
        <form className="panel-body auth-form" onSubmit={handleSubmit}>
          <label className="label" htmlFor="username">Demo role</label>
          <select
            id="username"
            className="search-input"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          >
            {DEMO_ACCOUNTS.map((account) => (
              <option key={account.username} value={account.username}>
                {account.label}
              </option>
            ))}
          </select>

          <label className="label" htmlFor="password">Password</label>
          <input
            id="password"
            className="search-input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />

          {error ? <div className="status-banner status-error">{error}</div> : null}

          <button className="button button-primary" type="submit" disabled={pending}>
            {pending ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
