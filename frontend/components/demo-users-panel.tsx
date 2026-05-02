"use client";

import { useEffect, useState } from "react";

import { getDemoUsers } from "@/lib/api";
import { DemoUser } from "@/lib/types";

export function DemoUsersPanel() {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadDemoUsers() {
      try {
        const result = await getDemoUsers();
        if (active) {
          setUsers(result.users);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load demo users");
        }
      }
    }

    void loadDemoUsers();

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <div className="section-kicker">Demo roles</div>
          <h2 className="panel-title">Interview personas</h2>
          <p className="panel-copy">Three walkthrough roles frame the product from clinical, operations, and data-quality angles.</p>
        </div>
      </div>
      <div className="panel-body">
        {error ? <div className="status-banner status-error">{error}</div> : null}
        <div className="list">
          {users.map((user) => (
            <article key={user.id} className="demo-user-card">
              <div>
                <strong>{user.name}</strong>
                <div className="meta-line">{user.role}</div>
              </div>
              <p>{user.focus}</p>
              <div className="pill-row">
                {user.permissions.slice(0, 3).map((permission) => (
                  <span key={permission} className="pill">
                    {permission.replaceAll("_", " ")}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
