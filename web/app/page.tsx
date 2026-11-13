"use client";

import { useCallback, useEffect, useState } from "react";

import { CompanyCard } from "@/components/CompanyCard";
import { CompanyDrawer } from "@/components/CompanyDrawer";
import { Header } from "@/components/Header";
import { SubscribeModal } from "@/components/SubscribeModal";
import { type Selection, TopicSidebar } from "@/components/TopicSidebar";
import {
  getCompanies,
  getCompany,
  getStats,
  getTaxonomy,
  type Company,
  type CompanyDetail,
  type Stats,
  type Taxonomy,
} from "@/lib/api";
import { titleCase } from "@/lib/format";

const FUNDING_GATE = 10_000_000;

export default function Page() {
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selection, setSelection] = useState<Selection>({});
  const [minFunding, setMinFunding] = useState(true);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState<CompanyDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [subscribeOpen, setSubscribeOpen] = useState(false);

  const refreshStats = useCallback(() => {
    getStats().then(setStats).catch(() => undefined);
  }, []);

  useEffect(() => {
    getTaxonomy().then(setTaxonomy).catch(() => undefined);
    refreshStats();
  }, [refreshStats]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const timer = setTimeout(async () => {
      try {
        const data = await getCompanies({
          ...selection,
          q: query || undefined,
          min_total_funding_usd: minFunding ? FUNDING_GATE : undefined,
        });
        if (!cancelled) setCompanies(data.companies);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load companies");
          setCompanies([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, query ? 250 : 0);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [selection, query, minFunding]);

  function toggleAxis(axis: "vertical" | "capability" | "buyer", label: string) {
    setSelection((prev) => ({ ...prev, [axis]: prev[axis] === label ? undefined : label }));
  }

  function clearFilters() {
    setSelection({});
    setMinFunding(false);
  }

  async function openDetail(id: string) {
    setDrawerOpen(true);
    setDetail(null);
    setDetailLoading(true);
    try {
      setDetail(await getCompany(id));
    } catch {
      setDrawerOpen(false);
    } finally {
      setDetailLoading(false);
    }
  }

  const activeFilters = [
    selection.vertical && `topic: ${titleCase(selection.vertical)}`,
    selection.capability && `subtopic: ${titleCase(selection.capability)}`,
    selection.buyer && `buyer: ${titleCase(selection.buyer)}`,
    minFunding && "> $10M",
  ].filter(Boolean) as string[];

  return (
    <div className="app">
      <Header
        stats={stats}
        active="explore"
        query={query}
        onQuery={setQuery}
        onSubscribe={() => setSubscribeOpen(true)}
      />

      <div className="main">
        <TopicSidebar
          taxonomy={taxonomy}
          selection={selection}
          minFunding={minFunding}
          onToggleAxis={toggleAxis}
          onMinFunding={setMinFunding}
          onClear={clearFilters}
        />

        <section>
          <div className="results-head">
            <h2>Explore AI startups</h2>
            <span className="muted">
              {loading ? "Loading…" : `${companies.length} result(s)`}
              {activeFilters.length > 0 && ` · ${activeFilters.join(" · ")}`}
            </span>
          </div>

          {error && <div className="error">{error} — is the API running?</div>}

          {!error && loading && (
            <div className="grid">
              {Array.from({ length: 6 }).map((_, i) => (
                <div className="skeleton" key={i} />
              ))}
            </div>
          )}

          {!error && !loading && companies.length === 0 && (
            <div className="empty">
              No startups match these filters yet. Try clearing a filter or lowering the funding gate.
            </div>
          )}

          {!error && !loading && companies.length > 0 && (
            <div className="grid">
              {companies.map((company) => (
                <CompanyCard key={company.id} company={company} onClick={() => openDetail(company.id)} />
              ))}
            </div>
          )}
        </section>
      </div>

      {drawerOpen && (
        <CompanyDrawer detail={detail} loading={detailLoading} onClose={() => setDrawerOpen(false)} />
      )}

      <SubscribeModal
        open={subscribeOpen}
        taxonomy={taxonomy}
        defaultVertical={selection.vertical}
        defaultCapability={selection.capability}
        onClose={() => {
          setSubscribeOpen(false);
          refreshStats();
        }}
      />
    </div>
  );
}
