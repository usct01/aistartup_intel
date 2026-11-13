# Funding Normalization Reference

Normative rules for turning raw funding claims into canonical `FundingRound` records
(`src/aistartup_intel/models/domain.py`) with consistent types, currencies, dates, and
thresholds.

## 1. Round types

`RoundType` (`src/aistartup_intel/models/enums.py`): `pre_seed`, `seed`, `series_a`, `series_b`,
`series_c`, `series_d`, `series_e`, `growth`, `debt`, `grant`, `ipo`, `undisclosed`, `other`.

- Map marketing names ("Series A extension", "seed+") to the nearest canonical value.
- When the stage cannot be determined, use `other` and lower confidence; do not guess a stage.

## 2. Funding types

`FundingType`: `equity`, `debt`, `grant`, `convertible`, `safe`, `other`.

- Classify the instrument, not just the label. A "grant" is `GRANT`; a venture loan is `DEBT`;
  a note or SAFE is `CONVERTIBLE` / `SAFE`; priced equity is `EQUITY`.
- Instrument type is independent of round type and must be recorded separately.

## 3. Disclosure status

`DisclosureStatus`: `disclosed`, `undisclosed`, `estimated`.

- `disclosed` — an amount is publicly stated by an authoritative source.
- `undisclosed` — a round is known to exist but no amount is stated.
- `estimated` — an amount is inferred, reported as a range, or third-party modelled.

## 4. Currency and USD normalization

- Store the original `amount` and `currency`, plus `amount_usd`.
- Normalize to USD using the rate appropriate to the transaction date, and record the basis.
- Never fabricate an amount to force normalization; if no amount exists, `amount_usd` stays
  null and disclosure is `undisclosed`.

## 5. Dates: announced vs. close

- `announced_on` — the date the round was publicly announced.
- `closed_on` — the actual close date where known.
- They may differ. Store both. Use `announced_on` for newsletter recency unless the close date
  is the material event. Do not overwrite one with the other.

## 6. Valuation

- `valuation_usd` is optional and recorded only when publicly disclosed. Never derive or infer
  a valuation from round size.

## 7. Thresholds (USD 10M)

Two **distinct** filters exist and must never be conflated:

- **Total publicly disclosed funding > USD 10M** — the sum across a company's qualifying rounds
  (`Company.total_disclosed_funding_usd`).
- **Individual round > USD 10M** — a single qualifying round's `amount_usd`.

Qualifying (counts toward numeric thresholds) means, per `FundingRound.counts_toward_threshold`:

- disclosure is `disclosed`, **and**
- `amount_usd` is present, **and**
- funding type is `equity`, `convertible`, or `safe`.

## 8. Exclusions from numeric thresholds

- `undisclosed` and `estimated` amounts are **labelled but excluded** from numeric thresholds.
- `debt`, `grant`, and `other` amounts do not count toward the equity-style total used for the
  funding gate, though they are stored and displayed.
- Never let an undisclosed or estimated figure push a company over the USD 10M line.

## 9. Conflicts and corrections

- When sources disagree on amount, date, or type, record all claims with confidences and list
  the conflict in `FundingAnalysis.conflicts`. Do not silently overwrite.
- Corrections are additive: set `correction_of` on the new record; keep the prior record and
  its history. The provenance ledger is append-only.
