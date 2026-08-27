"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { canInvestigateIngestion, canUpload, canViewAuditLogs, clearSession } from "@/lib/auth";
import { AuthUser } from "@/lib/types";


function initials(user: AuthUser) {
  const label = user.full_name || user.username;
  const parts = label.trim().split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") || "U";
}


type WorkspaceSection = "patients" | "ingestion" | "audit";


export function WorkspaceHeader({
  user,
  onSignOut,
  activeSection,
}: {
  user: AuthUser | null;
  onSignOut?: () => void;
  activeSection?: WorkspaceSection;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!menuOpen) return;

    function handlePointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen]);

  function handleSignOut() {
    if (onSignOut) {
      onSignOut();
      return;
    }
    clearSession();
    window.location.assign("/login");
  }

  return (
    <header className="workspace-header">
      <Link href="/" className="workspace-brand" aria-label="ClinSight AI home">
        <span className="workspace-brand-mark">C</span>
        <span>
          <strong>ClinSight AI</strong>
          <small>Clinical workspace</small>
        </span>
      </Link>

      {user ? (
        <>
          <nav className="workspace-nav" aria-label="Primary navigation">
            <Link
              href="/#patient-directory"
              className={`workspace-nav-link${activeSection === "patients" ? " active" : ""}`}
              aria-current={activeSection === "patients" ? "page" : undefined}
            >
              Patients
            </Link>
            {canUpload(user) ? <Link href="/#data-intake" className="workspace-nav-link">Data intake</Link> : null}
            {canInvestigateIngestion(user) ? (
              <Link
                href="/ingestion-runs"
                className={`workspace-nav-link${activeSection === "ingestion" ? " active" : ""}`}
                aria-current={activeSection === "ingestion" ? "page" : undefined}
              >
                Ingestion review
              </Link>
            ) : null}
            {canViewAuditLogs(user) ? (
              <Link
                href="/audit"
                className={`workspace-nav-link${activeSection === "audit" ? " active" : ""}`}
                aria-current={activeSection === "audit" ? "page" : undefined}
              >
                Audit trail
              </Link>
            ) : null}
          </nav>

          <div ref={menuRef} className={`user-menu${menuOpen ? " open" : ""}`}>
            <button
              ref={triggerRef}
              className="user-menu-trigger"
              type="button"
              aria-expanded={menuOpen}
              aria-haspopup="dialog"
              aria-controls="workspace-account-menu"
              onClick={() => setMenuOpen((current) => !current)}
            >
              <span className="user-avatar" aria-hidden="true">{initials(user)}</span>
              <span className="user-menu-identity">
                <strong>{user.full_name || user.username}</strong>
                <small>{user.role.replaceAll("_", " ")}</small>
              </span>
              <span className="user-menu-chevron" aria-hidden="true">⌄</span>
            </button>
            {menuOpen ? (
              <div id="workspace-account-menu" className="user-menu-popover" role="dialog" aria-label="Account menu">
                <div className="user-menu-context">
                  <span className="section-kicker">Signed in as</span>
                  <strong>{user.full_name || user.username}</strong>
                  <span className="meta-line">{user.username} · {user.role.replaceAll("_", " ")}</span>
                </div>
                <button className="sign-out-action" type="button" onClick={handleSignOut}>
                  Sign out
                </button>
              </div>
            ) : null}
          </div>
        </>
      ) : null}
    </header>
  );
}
