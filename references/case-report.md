# Case report / case series extraction schema (CARE-aligned)

For single cases (n=1) or small uncontrolled series. These are the **weakest** evidence — extract them, but keep `evidence_level: Low` and treat as hypothesis-generating, never confirmatory.

| Field key | Content |
|---|---|
| `n` | 1 (case report) or series size |
| `patient` | Brief patient/series description (relevant demographics, condition) |
| `intervention` | Intervention / exposure described |
| `outcome` | Observed outcome |
| `timeline` | Key timeline if relevant (onset → intervention → outcome) |
| `generalizability` | Why caution: no comparator, selection/reporting bias, single setting |

## Appraisal cues

- Always `evidence_level: Low`.
- A case report's value is **signal**, not proof. Useful for: novel adverse event, rare presentation, mechanism hypothesis.

## Synthesis reminders

- Never let a case report set the `direction` of the review's conclusion.
- In `synthesis_note`, frame as "raises the possibility that…", never "demonstrates" / "confirms".
- A cluster of case reports is still not a controlled study — do not aggregate them into an implied effect size.
