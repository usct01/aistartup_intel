export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export type TaxTag = { label: string; count: number };
export type Taxonomy = { axes: Record<string, TaxTag[]> };

export type Company = {
  id: string;
  name: string;
  url: string | null;
  hq: string | null;
  description: string | null;
  total_disclosed_funding_usd: number;
  confidence: number;
  is_new: boolean;
};

export type FundingRound = {
  id: string;
  round_type: string;
  amount_usd: number | null;
  announced_on: string | null;
  confidence: number;
};

export type LedgerEntry = { action: string; type: string; at: string };

export type CompanyDetail = Company & {
  funding_rounds: FundingRound[];
  taxonomy: { axis: string; label: string; confidence: number }[];
  ledger: LedgerEntry[];
};

export type Stats = { companies: number; pending_reviews: number; subscribers: number };

export type CompanyQuery = {
  vertical?: string;
  capability?: string;
  buyer?: string;
  q?: string;
  min_total_funding_usd?: number;
  limit?: number;
};

export type SubscribePayload = {
  email: string;
  name?: string;
  verticals: string[];
  capabilities: string[];
  min_funding_usd: number;
};

export type NewsletterItem = {
  company: string;
  headline: string;
  body: string;
  confidence: number;
  evidence_urls: string[];
  score: number | null;
};

export type NewsletterDraft = {
  subject: string;
  vertical_pulse: Record<string, string>;
  items: NewsletterItem[];
  generated_at: string | null;
};

async function getJson<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(API_BASE + path);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
    }
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as T;
}

export function getTaxonomy(): Promise<Taxonomy> {
  return getJson<Taxonomy>("/taxonomy");
}

export function getStats(): Promise<Stats> {
  return getJson<Stats>("/stats");
}

export function getCompanies(query: CompanyQuery): Promise<{ count: number; companies: Company[] }> {
  return getJson("/companies", {
    vertical: query.vertical,
    capability: query.capability,
    buyer: query.buyer,
    q: query.q,
    min_total_funding_usd: query.min_total_funding_usd,
    limit: query.limit ?? 60,
  });
}

export function getCompany(id: string): Promise<CompanyDetail> {
  return getJson<CompanyDetail>(`/companies/${id}`);
}

export function getSubscription(email: string): Promise<{
  email: string;
  subscribed: boolean;
  verticals: string[];
  capabilities: string[];
  min_funding_usd: number;
}> {
  return getJson("/newsletter/subscription", { email });
}

export async function previewNewsletter(
  verticals: string[],
  minFundingUsd: number,
): Promise<NewsletterDraft> {
  const url = new URL(API_BASE + "/newsletter/preview");
  for (const vertical of verticals) url.searchParams.append("verticals", vertical);
  url.searchParams.set("min_funding_usd", String(minFundingUsd));
  const res = await fetch(url.toString(), { method: "POST", cache: "no-store" });
  if (!res.ok) throw new Error(`Preview failed (${res.status})`);
  return (await res.json()) as NewsletterDraft;
}

export async function subscribe(payload: SubscribePayload): Promise<{ user_id: string }> {
  const res = await fetch(`${API_BASE}/newsletter/subscribe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail || `Subscribe failed (${res.status})`);
  }
  return (await res.json()) as { user_id: string };
}
