"use client";

import Link from "next/link";

import type { Stats } from "@/lib/api";

type Props = {
  stats: Stats | null;
  active?: "explore" | "briefing";
  query?: string;
  onQuery?: (value: string) => void;
  onSubscribe?: () => void;
};

export function Header({ stats, active, query, onQuery, onSubscribe }: Props) {
  return (
    <header className="header">
      <Link href="/" className="brand">
        <span className="dot" />
        AI Startup Signal
      </Link>

      <nav className="nav">
        <Link href="/" className={active === "explore" ? "active" : ""}>
          Explore
        </Link>
        <Link href="/briefing" className={active === "briefing" ? "active" : ""}>
          Briefing
        </Link>
      </nav>

      {onQuery ? (
        <label className="search">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
            <circle cx="11" cy="11" r="7" stroke="#6b7488" strokeWidth="2" />
            <path d="m20 20-3.2-3.2" stroke="#6b7488" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            value={query ?? ""}
            onChange={(e) => onQuery(e.target.value)}
            placeholder="Search startups by name…"
            aria-label="Search startups"
          />
        </label>
      ) : (
        <div style={{ flex: 1 }} />
      )}

      <div className="stats">
        <span>
          <b>{stats?.companies ?? "—"}</b> companies
        </span>
        <span>
          <b>{stats?.subscribers ?? "—"}</b> subscribers
        </span>
        <span>
          <b>{stats?.pending_reviews ?? "—"}</b> in review
        </span>
      </div>

      {onSubscribe && (
        <button className="btn primary" onClick={onSubscribe}>
          Subscribe
        </button>
      )}
    </header>
  );
}
