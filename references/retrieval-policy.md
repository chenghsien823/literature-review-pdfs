# Full-text retrieval policy

## Legal source priority

1. PubMed Central (PMCID) and Europe PMC open full text.
2. Open repository or publisher PDF URL returned by Unpaywall.
3. DOI publisher landing page, only as a browser-handoff link. It is never fetched as if it were a PDF.

The retrieval script downloads only candidates described as open access. It never supplies credentials, reuses browser cookies, evades a paywall, or solves a CAPTCHA.

Set UNPAYWALL_EMAIL (or NCBI_EMAIL) in the environment to enable Unpaywall's
open-location lookup. The script does not print either value.

## Statuses

| Status | Meaning | Next action |
|---|---|---|
| retrieved | PDF header and validation passed; local file and hash are recorded. | Review full text. |
| candidate_found_dry_run | A legal candidate was found but no file was saved. | Re-run without --dry-run. |
| needs_browser_session | A DOI landing page exists, but no open PDF was located. | Open it only in an already authenticated browser session. |
| not_found | No supported open source or publisher link was found. | Check library holdings, author manuscript, or request document delivery. |
| download_failed | An open candidate did not download successfully. | Review source URL and retry later; do not assume access is denied. |
| invalid_pdf | Response was not a valid PDF. | Inspect manually; do not rename it as a PDF. |
| input_error | The supplied record lacks usable identifiers or cannot be parsed. | Correct the source record. |

## Identifier and filename rules

- Deduplicate DOI first, then PMID, then a normalized title only when both identifiers are absent.
- Do not infer DOI from a title in this retrieval step.
- Use the default stable filename FirstAuthor_Year_Journal_DOIshort.pdf; add _2, _3, and so on rather than overwrite an existing file.
- When a review workflow requests --filename-style first-author-country-year, use FirstAuthor Country Year.pdf. Derive the country only from the first author's PubMed affiliation; use UnknownCountry and keep the manifest flag when it cannot be verified.
- Store a SHA-256 and page count where available. A successful request that returns HTML is not a retrieval.

## SRMA integration

When the target directory is 04_fulltext in an SRMA project, update manifest.csv using the existing columns:
record_id, citation, pmid, doi, retrieval_status, source, local_path_or_url, and notes.

Do not replace an existing retrieved row with a later failed or blocked result. PDFs may be kept locally but must not be committed to Git.
