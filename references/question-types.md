# Clinical question types — field spec

Pick `question_type` first; it sets required fields and query construction. `population` and `question_type` are always required. Boolean helpers (`and_terms`, `or_terms`, `not_terms`) and all filters are optional for every type.

`query.json` is a single object: common fields + type-specific fields.

## Common fields (all types)

| Field | Req | Notes |
|---|---|---|
| `question_type` | ✔ | therapy / risk_factor / diagnosis / prognosis / frequency |
| `population` | ✔ | the P — who/what condition |
| `date_from`, `date_to` | – | year bounds, e.g. 2015, 2025 |
| `max_results` | – | default 30 |
| `species` | – | e.g. "human" |
| `language` | – | e.g. "english" |
| `pub_types` | – | list, e.g. ["Randomized Controlled Trial","Meta-Analysis"] |
| `and_terms`, `or_terms`, `not_terms` | – | extra boolean refinement |
| `mesh_terms` | – | explicit MeSH terms to AND in (from --suggest-mesh) |

## ① therapy — intervention comparison

| Field | Req |
|---|---|
| `intervention` | ✔ |
| `comparator` | ✔ |
| `outcome` | ✔ |

Query: `population AND intervention AND comparator AND outcome` (+ filters). Tip: add pub_types RCT / Meta-Analysis.
Example:
```json
{"question_type":"therapy","population":"eosinophilic granulomatosis with polyangiitis",
 "intervention":"dupilumab","comparator":"mepolizumab","outcome":"relapse",
 "date_from":2018,"species":"human","max_results":30}
```

## ② risk_factor — etiology / harm

| Field | Req |
|---|---|
| `exposure` | ✔ |
| `comparator` | – (often implicit) |
| `outcome` | ✔ |

Query: `population AND exposure AND outcome` (+ filters). Tip: pub_types Cohort/Case-control aren't PubMed types — instead add or_terms ["cohort","case-control"].
Example:
```json
{"question_type":"risk_factor","population":"rheumatoid arthritis",
 "exposure":"JAK inhibitor","outcome":"venous thromboembolism",
 "or_terms":["cohort","case-control"],"date_from":2016,"species":"human"}
```

## ③ diagnosis — diagnostic accuracy

| Field | Req |
|---|---|
| `index_test` | ✔ |
| `reference_standard` | – |
| `target_condition` | ✔ |

Query: `population AND index_test AND target_condition` (+ "sensitivity OR specificity OR accuracy"). reference_standard ANDed if given.
Example:
```json
{"question_type":"diagnosis","population":"adults",
 "index_test":"lung ultrasound","target_condition":"pneumonia",
 "reference_standard":"chest CT","species":"human"}
```

## ④ prognosis

| Field | Req |
|---|---|
| `condition` | ✔ |
| `predictor` | – |
| `outcome` | ✔ |
| `timeframe` | – |

Query: `condition AND outcome AND (prognosis OR survival OR mortality OR recurrence)`; predictor/timeframe ANDed if given.
Example:
```json
{"question_type":"prognosis","population":"RA-associated interstitial lung disease",
 "condition":"RA-ILD","outcome":"mortality","timeframe":"5-year","species":"human"}
```

## ⑤ frequency — prevalence / incidence

| Field | Req |
|---|---|
| `condition` | ✔ |
| `setting` | – |
| `timeframe` | – |

Query: `population/condition AND (prevalence OR incidence OR epidemiology)`; setting/timeframe ANDed if given.
Example:
```json
{"question_type":"frequency","population":"general population",
 "condition":"eosinophilic granulomatosis with polyangiitis",
 "setting":"population-based","species":"human"}
```

## ⑥ scoping — broad-recall topic sweep

| Field | Req |
|---|---|
| `or_terms` (or `and_terms` / `mesh_terms`) | ✔ (at least one) |
| `population` | – (optional anchor; omit to sweep on candidate terms alone) |

Query: `population AND (or_terms)` if population given, else `(or_terms)` (+ `and_terms`, `mesh_terms`, filters). comparator/outcome are **ignored** — this mode maximises recall, not precision. Topic-agnostic: feed any candidate terms. Defaults to `sort:"relevance"`; raise `max_results` toward total `count` and screen the full pool downstream. Optional `with_abstracts:true` enriches records for screening.
Example:
```json
{"question_type":"scoping","population":"eosinophilic granulomatosis with polyangiitis",
 "or_terms":["mepolizumab","benralizumab","dupilumab","tezepelumab","JAK inhibitor","anti-IL-5"],
 "species":"human","max_results":300}
```

## Output (all types) — feeds lit-screen / evidence-extractor

Each record: `pmid`, `doi`, `title`, `authors`, `journal`, `year`, `abstract`, `publication_type`, `mesh`. These map onto evidence-extractor's shared columns; `publication_type` helps pick the extraction design schema.
