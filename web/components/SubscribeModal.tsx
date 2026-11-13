"use client";

import { useEffect, useState } from "react";

import { subscribe, type Taxonomy } from "@/lib/api";
import { titleCase } from "@/lib/format";

type Props = {
  open: boolean;
  onClose: () => void;
  taxonomy: Taxonomy | null;
  defaultVertical?: string;
  defaultCapability?: string;
};

export function SubscribeModal({
  open,
  onClose,
  taxonomy,
  defaultVertical,
  defaultCapability,
}: Props) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [verticals, setVerticals] = useState<string[]>([]);
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [minFunding, setMinFunding] = useState(10_000_000);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setVerticals(defaultVertical ? [defaultVertical] : []);
      setCapabilities(defaultCapability ? [defaultCapability] : []);
      setStatus("idle");
      setError("");
    }
  }, [open, defaultVertical, defaultCapability]);

  if (!open) return null;

  function toggle(list: string[], setList: (v: string[]) => void, value: string) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setError("");
    try {
      await subscribe({ email, name: name || undefined, verticals, capabilities, min_funding_usd: minFunding });
      setStatus("done");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  }

  const topicTags = taxonomy?.axes?.vertical ?? [];
  const subtopicTags = taxonomy?.axes?.capability ?? [];

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true">
        <h2>Subscribe to the daily briefing</h2>
        <p className="sub">
          Verified AI startup and funding signals, filtered to the topics you follow.
        </p>

        {status === "done" ? (
          <>
            <div className="msg ok">
              You&apos;re subscribed. We&apos;ll send verified updates for your selected topics.
            </div>
            <div className="form-actions">
              <button className="btn primary" onClick={onClose}>
                Done
              </button>
            </div>
          </>
        ) : (
          <form onSubmit={onSubmit}>
            {status === "error" && <div className="msg err">{error}</div>}

            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@fund.com"
              />
            </div>

            <div className="field">
              <label htmlFor="name">Name (optional)</label>
              <input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
            </div>

            <div className="field">
              <label>Topics</label>
              <div className="chips">
                {topicTags.map((tag) => (
                  <button
                    type="button"
                    key={tag.label}
                    className={`chip ${verticals.includes(tag.label) ? "active" : ""}`}
                    onClick={() => toggle(verticals, setVerticals, tag.label)}
                  >
                    {titleCase(tag.label)}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <label>Subtopics</label>
              <div className="chips">
                {subtopicTags.map((tag) => (
                  <button
                    type="button"
                    key={tag.label}
                    className={`chip ${capabilities.includes(tag.label) ? "active" : ""}`}
                    onClick={() => toggle(capabilities, setCapabilities, tag.label)}
                  >
                    {titleCase(tag.label)}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <label htmlFor="min">Minimum disclosed funding (USD)</label>
              <input
                id="min"
                type="number"
                min={0}
                step={1_000_000}
                value={minFunding}
                onChange={(e) => setMinFunding(Number(e.target.value))}
              />
            </div>

            <div className="form-actions">
              <button type="button" className="btn" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn primary" disabled={status === "loading"}>
                {status === "loading" ? "Subscribing…" : "Subscribe"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
