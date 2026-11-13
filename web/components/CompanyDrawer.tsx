"use client";

import type { CompanyDetail } from "@/lib/api";
import { formatDate, formatUsd, relativeTime, titleCase } from "@/lib/format";

type Props = {
  detail: CompanyDetail | null;
  loading: boolean;
  onClose: () => void;
};

export function CompanyDrawer({ detail, loading, onClose }: Props) {
  function closeOnBackdrop(e: React.MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div className="drawer-backdrop" onClick={closeOnBackdrop}>
      <div className="drawer" role="dialog" aria-modal="true">
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button className="close" onClick={onClose}>
            Close
          </button>
        </div>

        {loading || !detail ? (
          <>
            <div className="skeleton" style={{ height: 34, marginTop: 12 }} />
            <div className="skeleton" style={{ height: 120, marginTop: 20 }} />
          </>
        ) : (
          <>
            <h2>{detail.name}</h2>
            <div className="funding" style={{ fontSize: 26 }}>
              {formatUsd(detail.total_disclosed_funding_usd)} disclosed
            </div>
            {detail.description && (
              <p className="desc" style={{ WebkitLineClamp: 6, display: "block" }}>
                {detail.description}
              </p>
            )}
            <div className="tagrow" style={{ marginTop: 10 }}>
              {detail.url && (
                <a className="tag" href={detail.url} target="_blank" rel="noreferrer">
                  {new URL(detail.url).hostname}
                </a>
              )}
              {detail.hq && <span className="tag">{detail.hq}</span>}
              <span className="tag">confidence {(detail.confidence * 100).toFixed(0)}%</span>
            </div>

            <div className="section">
              <h3>Taxonomy</h3>
              <div className="tagrow">
                {detail.taxonomy.length === 0 && <span className="muted">No labels yet</span>}
                {detail.taxonomy.map((tag) => (
                  <span
                    key={`${tag.axis}-${tag.label}`}
                    className={`tag ${tag.axis === "vertical" ? "vertical" : ""}`}
                  >
                    {titleCase(tag.label)} · {(tag.confidence * 100).toFixed(0)}%
                  </span>
                ))}
              </div>
            </div>

            <div className="section">
              <h3>Funding rounds</h3>
              {detail.funding_rounds.length === 0 && (
                <div className="muted" style={{ color: "var(--text-dim)", fontSize: 13 }}>
                  No verified rounds yet.
                </div>
              )}
              {detail.funding_rounds.map((round) => (
                <div className="round" key={round.id}>
                  <span>
                    {titleCase(round.round_type)} · {formatDate(round.announced_on)}
                  </span>
                  <span className="amt">{formatUsd(round.amount_usd)}</span>
                </div>
              ))}
            </div>

            <div className="section">
              <h3>Evidence ledger (append-only)</h3>
              {detail.ledger.map((entry, index) => (
                <div className="ledger-item" key={index}>
                  <span className="type">{entry.type}</span>
                  <span>{entry.action}</span>
                  <span style={{ marginLeft: "auto" }}>{relativeTime(entry.at)}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
