# Shared columns (every study, every design)

Extract these for **all** studies regardless of design. They populate the Synthesis Master sheet and make studies comparable. The last four are the synthesis columns — the reason the table exists.

| Column | Content | Notes |
|---|---|---|
| `citation` | First author + year (e.g., "Smith 2023") | Short label |
| `pmid` | PubMed ID | NR if none |
| `doi` | DOI | NR if none |
| `verified` | `true` / `false` | Was the DOI/PMID actually checked to exist and match? Never mark true without checking. Unverified = likely fabrication; keep it false and flag it. |
| `design` | One of: RCT, Cohort, Case-control, Cross-sectional, Case report, Case series, Systematic review, Meta-analysis | Determines detail schema |
| `population` | One-line population / setting | |
| `key_finding` | The study's main result, one sentence, in your own words | Paraphrase, do not copy abstract |
| **`evidence_level`** | `High` / `Moderate` / `Low` | By design + execution: RCT/SR-MA high; cohort/case-control moderate; cross-sectional/case series low-moderate; case report low. Downgrade for serious limitations. |
| **`direction`** | `support` / `oppose` / `neutral` | Relative to the review's prevailing/working position. Rendered as ↑ / ↓ / → |
| **`conflict`** | Free text: which other study(ies) it contradicts, or empty | Flagged/highlighted in output. Do NOT smooth over real contradictions — surfacing them is the job. |
| **`synthesis_note`** | What gap this fills / what it adds / why it matters | The human's synthesis hook. May be drafted by AI but is the author's judgement. |

## Rules

- **Paraphrase**, never paste abstract text into `key_finding`.
- **NR for missing**, never blank, never invented.
- `evidence_level`, `direction`, `conflict`, `synthesis_note` are **judgement calls** — flag them for human confirmation; do not present them as settled fact.
- A study with `verified: false` should be visually flagged and **excluded from synthesis** until checked.
