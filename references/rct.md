# RCT extraction schema (CONSORT-aligned)

For randomized controlled trials. Put these under the study's `fields` object. Use `NR` for anything not reported.

| Field key | Content |
|---|---|
| `inclusion` | Key eligibility criteria |
| `intervention` | Intervention arm (drug/dose/regimen) |
| `comparator` | Comparator arm (placebo / active) |
| `randomization` | Method of sequence generation + allocation concealment (NR if unclear) |
| `blinding` | Open / single / double-blind; who was blinded |
| `n_total` | Total randomized; per-arm if available (e.g., "240 (120/120)") |
| `primary_outcome` | Pre-specified primary endpoint |
| `effect` | Effect estimate for primary outcome + 95% CI (e.g., "RR 0.78, 95% CI 0.64–0.95") |
| `analysis` | ITT / per-protocol / modified ITT |
| `followup` | Duration of follow-up |
| `funding_coi` | Funding source / declared conflicts (NR if absent) |

## Appraisal cues (feed into shared `evidence_level`)

- High: adequate randomization + allocation concealment + blinding + ITT + low attrition.
- Downgrade for: unclear/inadequate concealment, no blinding where feasible, high/differential dropout, selective outcome reporting, industry funding with no independent analysis.

## Synthesis reminders

- Record the **primary** outcome's effect, not the most favourable secondary one (guard against the paper's own cherry-picking).
- A non-significant CI crossing 1 (or 0 for differences) is a **neutral/▢ null** result — record it as such; do not phrase it as benefit.
