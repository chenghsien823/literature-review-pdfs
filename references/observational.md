# Observational study extraction schema (STROBE-aligned)

Covers **cohort**, **case-control**, **cross-sectional**. Shared observational fields first, then design-specific. Use `NR` for missing.

## Common observational fields

| Field key | Content |
|---|---|
| `exposure` | Exposure / determinant studied |
| `outcome` | Outcome studied |
| `n_total` | Analytic sample size |
| `confounding` | How confounding was handled: multivariable model / PSM / IPTW / matching / stratification / none (NR). **Critical field** — observational evidence lives or dies here. |
| `effect` | Adjusted effect estimate + 95% CI (HR/RR/OR/PR), and state which |
| `source` | Data source / setting (registry, EHR, cohort name) |

## Cohort-specific

| Field key | Content |
|---|---|
| `comparator` | Unexposed / reference group |
| `followup` | Follow-up duration; person-time if given |
| `incidence` | Incidence or cumulative incidence per group (if reported) |

## Case-control-specific

| Field key | Content |
|---|---|
| `case_def` | Case definition / source |
| `control_source` | Control source + matching variables |
| `exposure_ascertain` | How exposure was ascertained (interview / records) → recall bias risk |

## Cross-sectional-specific

| Field key | Content |
|---|---|
| `sampling` | Sampling frame / method |
| `temporality` | Note that exposure and outcome are measured simultaneously → no causal direction |

## Appraisal cues (feed into shared `evidence_level`)

- Moderate by default for cohort/case-control with adequate confounding control; Low–Moderate for cross-sectional.
- Downgrade for: no/weak confounding adjustment, selection bias, recall bias (case-control), reverse causation risk (cross-sectional), short follow-up, immortal-time bias.

## Synthesis reminders

- `confounding` is the single most important observational field — an unadjusted association is weak evidence; record exactly what was adjusted for.
- Cross-sectional associations are **not** causal — keep `direction`/`synthesis_note` cautious.
- Record the **adjusted** estimate; if only crude is given, say so.
