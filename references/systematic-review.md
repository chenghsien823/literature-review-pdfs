# Systematic review / meta-analysis extraction schema (PRISMA-aligned)

For predefined-search reviews and pooled analyses. These are typically the **strongest** synthesis-level evidence — but only if the search and appraisal were sound. Use `NR` for missing.

| Field key | Content |
|---|---|
| `question` | Review question (PICO) |
| `databases` | Databases searched + date of last search |
| `n_studies` | Number of studies included; total participants if pooled |
| `pooled_effect` | Pooled estimate + 95% CI (state model: fixed/random), or "narrative only" if not pooled |
| `heterogeneity` | I² (and/or τ², Q) if meta-analysis |
| `quality_tool` | Risk-of-bias / quality tool used: RoB 2, Newcastle-Ottawa, GRADE, AMSTAR, etc. (NR if none — major limitation) |
| `included_designs` | What designs were pooled (RCTs only? observational mixed in?) |

## Appraisal cues (feed into shared `evidence_level`)

- High when: comprehensive search, predefined protocol (e.g., PROSPERO), risk-of-bias assessed, appropriate pooling, low–moderate heterogeneity.
- Downgrade for: narrow/single-database search, no risk-of-bias assessment, pooling clinically heterogeneous studies, high I² ignored, mixing RCTs and observational without stratifying.

## Synthesis reminders

- A meta-analysis pooling biased studies is **precise but not accurate** — high precision ≠ high evidence. Check `quality_tool`.
- High I² (e.g., >75%) means the pooled estimate may be meaningless — record it and stay cautious in `synthesis_note`.
- Distinguish "systematic review with meta-analysis" from "systematic review, narrative synthesis only".
