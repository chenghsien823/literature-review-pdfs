---
name: literature-review-pdfs
description: Build a PubMed narrative-review evidence package and offer legal full-text PDF retrieval for its screened studies. Use when Codex needs to find literature for a review, create a PubMed search log, evidence table, or research-gap map, then ask whether to obtain included papers' PDFs; also trigger on 文獻搜尋、找文獻、廣掃、證據表、研究缺口、下載全文、下載文獻 PDF、narrative review, or full-text retrieval after a literature search. Preserve the distinction between automated retrieval and human evidence judgement. Download only legally accessible PDFs and never bypass paywalls, CAPTCHAs, cookies, Cloudflare, or access controls.
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

## 1. Search and evidence package

1. Create or validate query.json.
2. Run:

~~~text
python scripts/run_pipeline.py query.json outdir --extraction extraction.json
~~~

3. Keep these outputs unchanged:
   - 01_search_log.xlsx: objective PubMed identification record.
   - 02_evidence_table.xlsx: reviewed evidence table.
   - 03_gap_map.xlsx: reviewer-confirmed synthesis aid.

Use --auto only to create a DRAFT scaffold. Do not treat its metadata-derived rows, evidence levels, directions, or gaps as verified conclusions.

For high-recall searches, include singular/plural, acronym, and hyphenation variants in each concept's aliases (for example, `SGLT2i`, `SGLT2 inhibitors`, and `sodium-glucose co-transporter 2 inhibitors`). When a known eligible PMID is available, add it as `required_pmids`; a missing PMID produces an explicit recall-check warning instead of a silently incomplete result set.

## 2. Required download check-in

After showing the search results and after a reviewed extraction.json exists, always ask:

> 是否要下載已納入研究中可合法取得的全文 PDF？

State the number of verified:true studies that can be prepared. Do not ask this question for a DRAFT-only extraction; explain that screening and identifier verification are required first.

- If the answer is no, deliver the evidence package and leave records.json available for a later run.
- If the answer is yes, prepare only the reviewed included studies. Never silently substitute all PubMed hits.

## 3. Prepare selected studies

~~~text
python scripts/prepare_fulltext_input.py outdir/records.json extraction.json outdir/included_records.json
~~~

The helper matches DOI first and PMID second. It writes only verified included records and reports unmatched or unverified rows. Stop and resolve an empty selection or unmatched record before claiming the download set is complete.

## 4. Retrieve legal full text

First inspect legal candidates:

~~~text
python scripts/retrieve_fulltext.py --input outdir/included_records.json --output-dir outdir/fulltext --filename-style first-author-country-year --dry-run
~~~

After the user has confirmed download, run the same command without --dry-run. Report the manifest status counts rather than implying every paper was retrieved.

The preferred PDF filename is FirstAuthor Country Year.pdf. Derive the country from the first author's PubMed affiliation. If it cannot be reliably verified, retain the legal download as FirstAuthor UnknownCountry Year.pdf and flag it in retrieval_manifest.csv.

Use PMC, Europe PMC (including its `fullTextPDF` REST endpoint), and Unpaywall-provided open locations first. A publisher PDF may be used only when its public landing page explicitly declares Open Access (or a Creative Commons licence) and supplies a public PDF URL; validate the downloaded bytes as usual. If a metadata source is unavailable, record `lookup_failed` rather than `not_found`, then retry in an authorized network context. For needs_browser_session, open the publisher landing page only through an already authenticated browser session and only if the user is entitled to access. Never export cookies, enter credentials, solve CAPTCHAs, or defeat a paywall.

## Completion wording

Call a PDF retrieved only when its manifest status is retrieved, with validated PDF bytes, local path, SHA-256, and page count where available. Keep PDFs and browser downloads out of Git.
