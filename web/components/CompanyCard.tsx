"use client";

import type { Company } from "@/lib/api";
import { formatUsd } from "@/lib/format";

export function CompanyCard({ company, onClick }: { company: Company; onClick: () => void }) {
  return (
    <article className="card" onClick={onClick} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}>
      <div className="card-top">
        <h3>{company.name}</h3>
        {company.is_new && <span className="badge">New</span>}
      </div>

      <div className="funding">{formatUsd(company.total_disclosed_funding_usd)}</div>

      {company.description ? (
        <p className="desc">{company.description}</p>
      ) : (
        <p className="desc">AI startup tracked by the signal platform.</p>
      )}

      <div className="meta">
        <span>{company.hq || "Location unknown"}</span>
        <span>confidence {(company.confidence * 100).toFixed(0)}%</span>
      </div>
    </article>
  );
}
