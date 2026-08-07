# Design selection — identify the study design first

Pick the design before extracting; it determines the schema. Decision cues:

- **Randomized controlled trial (RCT)** — participants randomly allocated to intervention vs comparator. Look for "randomized", "allocation", "double-blind", "placebo-controlled". → `references/rct.md` (CONSORT)
- **Cohort** — defined groups by exposure status, followed forward for outcomes; reports incidence, HR/RR. → `references/observational.md`
- **Case-control** — starts from outcome (cases vs controls), looks back at exposure; reports OR. → `references/observational.md`
- **Cross-sectional** — exposure and outcome measured at one time point; reports prevalence / association, no temporality. → `references/observational.md`
- **Case report (n=1) / case series (small n, no comparator)** — descriptive, no control group. → `references/case-report.md` (CARE)
- **Systematic review / meta-analysis** — predefined search, multiple studies pooled or narratively synthesised; reports pooled estimate, heterogeneity. → `references/systematic-review.md` (PRISMA)

## Edge cases

- "Retrospective cohort" is still **Cohort**.
- "Nested case-control" is **Case-control**.
- A narrative/expert review without a systematic search is **not** a systematic review — extract it as background, not as evidence; mark `evidence_level: Low`.
- If a paper reports both a systematic review and a new meta-analysis, treat as **Meta-analysis**.
- If genuinely ambiguous, extract shared columns + closest design schema, and note the uncertainty in `synthesis_note`.
