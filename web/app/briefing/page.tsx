"use client";

import { useEffect, useState } from "react";

import { Header } from "@/components/Header";
import {
  getStats,
  getTaxonomy,
  previewNewsletter,
  type NewsletterDraft,
  type NewsletterItem,
  type Stats,
  type Taxonomy,
} from "@/lib/api";
import { formatUsd, titleCase } from "@/lib/format";
import { draftToMarkdown, draftToText, itemHeadline } from "@/lib/newsletter";

const FUNDING_GATE = 10_000_000;

export default function BriefingPage() {
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [verticals, setVerticals] = useState<string[]>([]);
  const [minFunding, setMinFunding] = useState(FUNDING_GATE);
  const [draft, setDraft] = useState<NewsletterDraft | null>(null);
  const [mode, setMode] = useState<"preview" | "edit">("preview");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<"" | "md" | "txt">("");

  useEffect(() => {
    getTaxonomy().then(setTaxonomy).catch(() => undefined);
    getStats().then(setStats).catch(() => undefined);
  }, []);

  function toggleVertical(label: string) {
    setVerticals((prev) =>
      prev.includes(label) ? prev.filter((v) => v !== label) : [...prev, label],
    );
  }

  async function generate() {
    setLoading(true);
    setError("");
    try {
      setDraft(await previewNewsletter(verticals, minFunding));
      setMode("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate briefing");
    } finally {
      setLoading(false);
    }
  }

  function updateSubject(value: string) {
    setDraft((d) => (d ? { ...d, subject: value } : d));
  }

  function updateItem(index: number, patch: Partial<NewsletterItem>) {
    setDraft((d) => {
      if (!d) return d;
      const items = d.items.map((item, i) => (i === index ? { ...item, ...patch } : item));
      return { ...d, items };
    });
  }

  async function copy(kind: "md" | "txt") {
    if (!draft) return;
    const text = kind === "md" ? draftToMarkdown(draft) : draftToText(draft);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      setTimeout(() => setCopied(""), 1500);
    } catch {
      setError("Clipboard unavailable in this browser context");
    }
  }

  const topicTags = taxonomy?.axes?.vertical ?? [];
  const pulse = draft ? Object.entries(draft.vertical_pulse) : [];
  const mailto = draft
    ? `mailto:?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(
        draftToText(draft),
      )}`
    : "#";

  return (
    <div className="app">
      <Header stats={stats} active="briefing" />

      <div className="briefing-grid">
        <aside className="panel briefing-controls">
          <h3>Briefing filters</h3>

          <div className="filter-group">
            <h3>Topics</h3>
            <div className="chips">
              {topicTags.length === 0 && (
                <span style={{ color: "var(--text-faint)", fontSize: 13 }}>Loading…</span>
              )}
              {topicTags.map((tag) => (
                <button
                  key={tag.label}
                  className={`chip ${verticals.includes(tag.label) ? "active" : ""}`}
                  onClick={() => toggleVertical(tag.label)}
                >
                  {titleCase(tag.label)}
                  <span className="count">{tag.count}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label htmlFor="min">Minimum disclosed funding</label>
            <input
              id="min"
              type="number"
              min={0}
              step={1_000_000}
              value={minFunding}
              onChange={(e) => setMinFunding(Number(e.target.value))}
            />
          </div>

          <button className="btn primary" style={{ width: "100%" }} onClick={generate} disabled={loading}>
            {loading ? "Generating…" : draft ? "Regenerate briefing" : "Generate briefing"}
          </button>

          {error && <div className="msg err" style={{ marginTop: 14 }}>{error}</div>}

          <p className="hint">
            Editions only include updates with verified funding evidence and confidence ≥ 50%.
          </p>
        </aside>

        <section>
          {!draft ? (
            <div className="panel empty">
              Choose topics and generate a briefing to preview the investor edition.
            </div>
          ) : (
            <>
              <div className="results-head">
                <h2>Briefing preview</h2>
                <div className="toolbar">
                  <div className="segmented">
                    <button
                      className={mode === "preview" ? "active" : ""}
                      onClick={() => setMode("preview")}
                    >
                      Preview
                    </button>
                    <button className={mode === "edit" ? "active" : ""} onClick={() => setMode("edit")}>
                      Edit
                    </button>
                  </div>
                  <button className="btn" onClick={() => copy("md")}>
                    {copied === "md" ? "Copied" : "Copy Markdown"}
                  </button>
                  <button className="btn" onClick={() => copy("txt")}>
                    {copied === "txt" ? "Copied" : "Copy text"}
                  </button>
                  <a className="btn" href={mailto}>
                    Email
                  </a>
                </div>
              </div>

              {mode === "edit" ? (
                <div className="panel" style={{ marginBottom: 16 }}>
                  <div className="field">
                    <label htmlFor="subject">Subject</label>
                    <input id="subject" value={draft.subject} onChange={(e) => updateSubject(e.target.value)} />
                  </div>
                  {draft.items.map((item, index) => (
                    <div key={index} className="item-editor">
                      <div className="field">
                        <label>Item {index + 1} — headline</label>
                        <input
                          value={item.headline}
                          onChange={(e) => updateItem(index, { headline: e.target.value })}
                        />
                      </div>
                      <div className="field">
                        <label>Body</label>
                        <textarea
                          rows={3}
                          value={item.body}
                          onChange={(e) => updateItem(index, { body: e.target.value })}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              <div className="email-preview">
                <div className="email-subject">{draft.subject}</div>
                <p className="email-greeting">Hi there,</p>
                <p className="email-intro">
                  Here is your AI Startup Signal briefing for {new Date().toLocaleDateString()}.
                </p>

                {pulse.length > 0 && (
                  <div className="email-pulse">
                    {pulse.map(([vertical, summary]) => (
                      <div key={vertical}>
                        <b>{titleCase(vertical)}</b> — {summary}
                      </div>
                    ))}
                  </div>
                )}

                {draft.items.length === 0 && (
                  <p className="email-empty">
                    No items met the verified-evidence bar for these filters.
                  </p>
                )}

                {draft.items.map((item, index) => (
                  <div className="email-item" key={index}>
                    <div className="email-item-head">
                      <h3>{itemHeadline(item)}</h3>
                      <span className="conf">{Math.round(item.confidence * 100)}% confidence</span>
                    </div>
                    <p>{item.body}</p>
                    {item.evidence_urls.length > 0 && (
                      <div className="email-sources">
                        Sources:{" "}
                        {item.evidence_urls.map((url, i) => (
                          <a key={i} href={url} target="_blank" rel="noreferrer">
                            [{i + 1}]
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                <div className="email-footer">
                  AI Startup Signal · verified AI funding intelligence · funding gate{" "}
                  {formatUsd(minFunding)}
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
