# Editorial Style Reference

Guidance for every agent that produces prose, and specifically for the Newsletter Editor and
Signal Analyst. The audience is **investors**: knowledgeable, time-poor, and allergic to hype.

## 1. Voice and tone

- Analyst-style, not marketing. Neutral, precise, confident where evidence is strong and
  explicitly uncertain where it is not.
- Investor-oriented: lead with what changed and why it matters to a portfolio, thesis, or
  market map — not with promotional adjectives.
- Concise. One clear point per sentence. Prefer plain words over jargon.
- No hype words ("revolutionary", "game-changing", "unprecedented", "disrupting") unless the
  source itself is being quoted verbatim and attributed.
- No emojis. No exclamation points. No clickbait subjects.

## 2. Evidence-linked claims

- Every factual assertion links to retained evidence (a source URL and its evidence span).
- Do not state a number, date, investor name, or funding amount that is not backed by a
  verbatim span in a retained document.
- Attribute reporting to its source ("per the company's announcement", "according to [filing]").
- If a fact is disputed or single-sourced, say so.

## 3. No speculation beyond evidence

- Interpretation is allowed when it is clearly reasoning *from* cited evidence ("the round size
  suggests the company is scaling GTM"), but never invents facts not present in the evidence.
- Do not forecast outcomes, valuations, or exits as if they were facts.
- Do not imply endorsement, financial advice, or investment recommendations. The product is
  research intelligence, not advice.
- Label uncertainty explicitly ("undisclosed", "reported, not confirmed").

## 4. Structure for a newsletter edition

- Subject line: specific and factual ("Acme Health raises $40M Series B; two new legal-AI
  launches"), not vague or sensational.
- Per item: company, one-line headline, a short evidence-linked body, a confidence value, and
  evidence URLs (`NewsletterItem`).
- Vertical pulse: a concise, evidence-aware sentence per subscribed vertical
  (`NewsletterDraft.vertical_pulse`). No fabricated market statistics.
- Prioritise verified, investor-relevant developments; exclude unverified or conflicted items.
- Personalise to the subscriber's sectors, thesis, and watchlist without distorting the facts.

## 5. Handling uncertainty and conflict

- When sources conflict, present the conflict plainly rather than choosing a side.
- When a claim is below the publish threshold, omit it or move it to a "watch" note — never
  dress it up as fact.
- Corrections are issued transparently; the newsletter is idempotent and re-publishing a
  corrected edition must not silently mutate history.

## 6. Length

- Tight. Each item should be readable in a few seconds. If an item needs more than a short
  paragraph, it is probably two items or belongs in the platform, not the email.
