import type { NewsletterDraft, NewsletterItem } from "@/lib/api";

export function itemHeadline(item: NewsletterItem): string {
  return item.headline || `${item.company} update`;
}

export function draftToText(draft: NewsletterDraft): string {
  const lines = [draft.subject, ""];
  const pulse = Object.entries(draft.vertical_pulse);
  if (pulse.length > 0) {
    lines.push("Market pulse:");
    for (const [vertical, summary] of pulse) lines.push(`  • ${vertical}: ${summary}`);
    lines.push("");
  }
  for (const item of draft.items) {
    lines.push(`— ${itemHeadline(item)}`);
    lines.push(item.body);
    if (item.evidence_urls.length > 0) lines.push(`Sources: ${item.evidence_urls.join(", ")}`);
    lines.push("");
  }
  return lines.join("\n").trim();
}

export function draftToMarkdown(draft: NewsletterDraft): string {
  const lines = [`# ${draft.subject}`, ""];
  const pulse = Object.entries(draft.vertical_pulse);
  if (pulse.length > 0) {
    lines.push("## Market pulse", "");
    for (const [vertical, summary] of pulse) lines.push(`- **${vertical}** — ${summary}`);
    lines.push("");
  }
  for (const item of draft.items) {
    lines.push(`### ${itemHeadline(item)}`);
    lines.push(item.body);
    if (item.evidence_urls.length > 0) {
      for (const url of item.evidence_urls) lines.push(`- [source](${url})`);
    }
    lines.push("");
  }
  return lines.join("\n").trim();
}
