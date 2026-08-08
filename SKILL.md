---
name: literature-review-pdfs
description: Build a PubMed narrative-review evidence package with an agent-friendly, auditable title/abstract screening queue, then offer legal full-text PDF retrieval for human-confirmed included studies. Use when Codex needs to find or screen literature for a review, create a PubMed search log, screening queue, evidence table, or research-gap map, or obtain legal full texts. Also trigger on 文獻搜尋、篩選文獻、初篩、找文獻、廣掃、證據表、研究缺口、下載全文、下載文獻 PDF, narrative review, or full-text retrieval after a literature search. Preserve the distinction between AI drafting and human evidence judgement. Download only legally accessible PDFs and never bypass paywalls, CAPTCHAs, cookies, Cloudflare, or access controls.
---

# 文獻搜尋與全文下載

Use this self-contained skill to search PubMed, create an auditable evidence package, and optionally retrieve legal full text for screened studies.

## Prerequisites

Require Python 3.10 or later. Install the public dependency:

~~~text
python -m pip install -r requirements.txt
~~~

For a new installation, run `check_setup.cmd` on Windows or `python scripts/check_setup.py` on macOS/Linux before the first PubMed search. This offline check verifies the bundled files, Python dependency, and command launchers; it never sends the user's configuration values anywhere.

Before a PubMed request, set NCBI_EMAIL to a real contact address. Optionally set NCBI_API_KEY for the higher NCBI request limit. Keep those values in the user's environment or an explicitly supplied local env file; never place them in this skill, output files, or version control.

## 0. Confirm review type before searching

Before creating `query.json`, ask exactly which route is intended: `narrative_scoping` or `srma`. Do not infer this from the topic. Write the answer to `query.json` as `review_type`.

- `narrative_scoping`: use for broad mapping, narrative synthesis, or identifying research gaps. Export `01_search_log.xlsx`, `02_evidence_table.xlsx`, and `03_gap_map.xlsx`.
- `srma`: use only for a protocol-driven systematic review with possible meta-analysis. Export `01_search_log.xlsx`, `02_srma_screening_register.xlsx`, `03_srma_data_extraction.xlsx`, `04_srma_risk_of_bias.xlsx`, and `05_srma_meta_analysis_input.xlsx`. Use the `srma-pipeline` workflow for protocol, independent human screening, effect-size validation, analysis, and PRISMA gates.

SRMA mode creates templates and an audit snapshot; it does not pool data, assign risk-of-bias judgments, or turn AI decisions into final eligibility.

## 1. Search and objective identification record

1. Create or validate query.json.
2. Run:

~~~text
python scripts/run_pipeline.py query.json outdir --extraction extraction.json
~~~

3. For `narrative_scoping`, keep these outputs unchanged:
   - 01_search_log.xlsx: objective PubMed identification record.
   - records.json: machine-readable source for screening.

For `srma`, `run_pipeline.py` creates the five SRMA-specific workbooks listed above. Keep canonical screening decisions in `02_screening/*.jsonl`; the screening workbook is an auditable human-review snapshot, not the decision database.

Do not treat `--auto` output as a screened evidence set. It is a metadata-only DRAFT scaffold.

## 2. Screen with the local structured queue

Do not use Excel as the screening database. Create a stable, agent-readable queue after the search:

~~~text
python scripts/create_screening_queue.py outdir/records.json outdir/02_screening
~~~

The first run writes `02_screening/screening_criteria.json` and exits. Define the review question, inclusion criteria, and protocol-specific exclusion reasons; then rerun the command. The completed run creates:

- `screening_candidates.jsonl`: immutable, source-linked candidate records for an agent.
- `agent_screening_instructions.md`: the exact draft-decision schema.
- `review_queue.html`: local human reviewer helper. Export its decisions as `reviewer_decisions.jsonl`.
- `screening_manifest.json`: source and count audit record.

Ask the agent to write a separate `ai_screening_draft.jsonl`. Each decision must be `include`, `exclude`, or `needs_fulltext`, with per-criterion results, an abstract-grounded rationale, an exclusion reason when applicable, confidence, reviewer identity, and timestamp. Never let the agent edit the candidate records or silently overwrite human decisions.

Validate any draft or reviewer decision file before using it:

~~~text
python scripts/validate_screening_decisions.py outdir/02_screening/screening_candidates.jsonl outdir/02_screening/ai_screening_draft.jsonl
~~~

AI decisions are DRAFT only. A human reviewer must confirm every AI `include` and `needs_fulltext`, and audit a protocol-appropriate sample of AI exclusions. For systematic reviews or meta-analyses, use independent human screening and conflict adjudication; an AI agent is not an independent reviewer.

Only after title/abstract and, when needed, full-text eligibility is human-confirmed may a record be written into `extraction.json` with `verified: true`. For `narrative_scoping`, then generate:

- `02_evidence_table.xlsx`: reviewed evidence table.
- `03_gap_map.xlsx`: reviewer-confirmed synthesis aid.

Keep human eligibility decisions, data extraction, interpretation, evidence levels, directions, and gap statements distinct. Do not treat metadata-derived rows, evidence levels, directions, or gaps as verified conclusions.

For `srma`, populate data extraction, risk-of-bias, and effect-size sheets only after the relevant human gate. Do not use `05_srma_meta_analysis_input.xlsx` as a pooled result or bypass estimand/PICOS and analysis-plan checks.

For high-recall searches, include singular/plural, acronym, and hyphenation variants in each concept's aliases (for example, `SGLT2i`, `SGLT2 inhibitors`, and `sodium-glucose co-transporter 2 inhibitors`). When a known eligible PMID is available, add it as `required_pmids`; a missing PMID produces an explicit recall-check warning instead of a silently incomplete result set.

## 3. Required download check-in

After showing the search results and after a reviewed extraction.json exists, always ask:

> 是否要下載已納入研究中可合法取得的全文 PDF？

State the number of verified:true studies that can be prepared. Do not ask this question for a DRAFT-only extraction; explain that screening and identifier verification are required first.

- If the answer is no, deliver the evidence package and leave records.json available for a later run.
- If the answer is yes, prepare only the reviewed included studies. Never silently substitute all PubMed hits.

## 4. Prepare selected studies

~~~text
python scripts/prepare_fulltext_input.py outdir/records.json extraction.json outdir/included_records.json
~~~

The helper matches DOI first and PMID second. It writes only verified included records and reports unmatched or unverified rows. Stop and resolve an empty selection or unmatched record before claiming the download set is complete.

## 5. Retrieve legal full text

First inspect legal candidates:

~~~text
python scripts/retrieve_fulltext.py --input outdir/included_records.json --output-dir outdir/fulltext --filename-style first-author-country-year --dry-run
~~~

After the user has confirmed download, run the same command without --dry-run. Report the manifest status counts rather than implying every paper was retrieved.

The preferred PDF filename is FirstAuthor Country Year.pdf. Derive the country from the first author's PubMed affiliation. If it cannot be reliably verified, retain the legal download as FirstAuthor UnknownCountry Year.pdf and flag it in retrieval_manifest.csv.

Use PMC, Europe PMC (including its `fullTextPDF` REST endpoint), and Unpaywall-provided open locations first. A publisher PDF may be used only when its public landing page explicitly declares Open Access (or a Creative Commons licence) and supplies a public PDF URL; validate the downloaded bytes as usual. If a metadata source is unavailable, record `lookup_failed` rather than `not_found`, then retry in an authorized network context. For needs_browser_session, open the publisher landing page only through an already authenticated browser session and only if the user is entitled to access. Never export cookies, enter credentials, solve CAPTCHAs, or defeat a paywall.

## Completion wording

Call a PDF retrieved only when its manifest status is retrieved, with validated PDF bytes, local path, SHA-256, and page count where available. Keep PDFs and browser downloads out of Git.
