# Literature Review PDFs

An installable Codex skill for an auditable PubMed narrative-review workflow:

1. Search PubMed and preserve an objective search log.
2. Build a design-aware evidence table and an intervention-outcome gap map.
3. Keep screening, study selection, and synthesis judgement under human review.
4. Ask whether to retrieve legal full-text PDFs for the verified included studies.
5. Retrieve only openly accessible PDFs and maintain a retrieval manifest.

## Install

Clone this repository into your Codex skills directory:

~~~text
git clone https://github.com/chenghsien823/literature-review-pdfs.git ~/.codex/skills/literature-review-pdfs
~~~

Alternatively, download the repository ZIP, extract it, and place the extracted folder at:

~~~text
~/.codex/skills/literature-review-pdfs
~~~

The folder must contain SKILL.md at its root. Restart Codex or start a new task after installation so the skill can be discovered.

## Prerequisites

- Python 3.10 or later
- A real NCBI contact email

Install the public dependency from the skill directory:

~~~text
python -m pip install -r requirements.txt
~~~

Before running a PubMed search, configure NCBI_EMAIL. NCBI_API_KEY is optional and only raises the request-rate limit.

Windows PowerShell:

~~~powershell
$env:NCBI_EMAIL = "you@example.org"
~~~

macOS or Linux:

~~~bash
export NCBI_EMAIL="you@example.org"
~~~

Keep credentials in environment variables or an explicitly selected local env file. Do not commit them to Git or place them in this repository.

## Basic workflow

Create a query.json, then build the evidence package:

~~~text
python scripts/run_pipeline.py query.json outdir --extraction extraction.json
~~~

This produces:

- 01_search_log.xlsx: objective PubMed identification record
- 02_evidence_table.xlsx: reviewed evidence table
- 03_gap_map.xlsx: reviewer-confirmed synthesis aid

Use --auto only for a DRAFT scaffold. It is not verified evidence and must not be presented as a finished synthesis.

After completing screening and a reviewed extraction.json, prepare only verified included studies for full-text retrieval:

~~~text
python scripts/prepare_fulltext_input.py outdir/records.json extraction.json outdir/included_records.json
~~~

Inspect legal full-text candidates first:

~~~text
python scripts/retrieve_fulltext.py --input outdir/included_records.json --output-dir outdir/fulltext --filename-style first-author-country-year --dry-run
~~~

Run the same command without --dry-run only after confirming that download is wanted.

## Access and safety

The skill uses PMC, Europe PMC, and Unpaywall open locations. It validates PDF bytes, records SHA-256 and page-count information where available, and writes retrieval_manifest.csv.

It does not bypass paywalls, CAPTCHAs, Cloudflare, cookies, access controls, or institutional authentication. When an article needs entitled browser access, it provides a manual handoff instead of attempting to authenticate.

## License

MIT. See LICENSE.
