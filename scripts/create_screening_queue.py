#!/usr/bin/env python3
"""Create an agent-friendly, auditable title/abstract screening queue."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CRITERIA = {
    "review_title": "",
    "review_question": "",
    "stage": "title_abstract",
    "inclusion_criteria": [
        {"id": "population", "question": "Does the title/abstract match the target population?"},
        {"id": "concept", "question": "Does it evaluate the target intervention, exposure, or concept?"},
        {"id": "evidence", "question": "Is it an eligible study type for this review?"},
    ],
    "exclusion_reasons": [
        {"id": "wrong_population", "label": "Wrong population or condition"},
        {"id": "wrong_concept", "label": "Wrong intervention, exposure, or concept"},
        {"id": "wrong_design", "label": "Ineligible publication or study design"},
        {"id": "wrong_outcome", "label": "Wrong outcome or scope"},
        {"id": "not_primary_study", "label": "Not a primary study for this review"},
        {"id": "duplicate", "label": "Duplicate record"},
        {"id": "other", "label": "Other protocol-defined reason"},
    ],
}

DECISION_PROMPT = """# Agent title/abstract screening instructions

Read `screening_criteria.json` and `screening_candidates.jsonl`. Write one JSON object per
candidate to `ai_screening_draft.jsonl`; do not modify the candidate file. Each object must contain:

```json
{
  "record_id": "...",
  "stage": "title_abstract",
  "decision": "include | exclude | needs_fulltext",
  "criteria_assessment": [
    {"criterion_id": "population", "result": "yes | no | unknown", "evidence": "brief abstract-grounded reason"}
  ],
  "exclusion_reason_id": "required only for exclude",
  "rationale": "brief, record-grounded rationale",
  "confidence": "low | medium | high",
  "reviewer_type": "ai",
  "reviewer_name": "model/workflow name",
  "decided_at_utc": "ISO-8601 UTC timestamp"
}
```

Rules:

- Never invent information absent from title/abstract. Use `needs_fulltext` when eligibility is unclear.
- Quote only the minimum useful phrase in `evidence`; do not write synthesis conclusions.
- An AI decision is a DRAFT. It cannot set `human_final: true`, `verified: true`, or trigger evidence synthesis/full-text download.
- A human reviewer must confirm every AI `include` and `needs_fulltext`, and should audit a sample of AI exclusions.
"""


def load_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        payload = payload.get("records", payload.get("studies", []))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("records_json must be a JSON list or an object containing records/studies.")
    return payload


def record_id(record: dict[str, Any]) -> str:
    for key in ("pmid", "doi"):
        value = str(record.get(key) or "").strip()
        if value:
            return f"{key}:{value.casefold()}"
    basis = "\n".join(str(record.get(key) or "").strip() for key in ("title", "year", "authors"))
    return "record:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def queue_record(record: dict[str, Any], source: Path) -> dict[str, Any]:
    keep = ("pmid", "doi", "title", "abstract", "authors", "journal", "year", "publication_type", "url")
    metadata = {key: record.get(key, "") for key in keep}
    fingerprint = hashlib.sha256(json.dumps(metadata, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "record_id": record_id(record),
        "source": {"records_json": str(source.resolve()), "record_sha256": fingerprint},
        "record": metadata,
        "screening": {"stage": "title_abstract", "status": "pending"},
    }


def html_page(candidates: list[dict[str, Any]], criteria: dict[str, Any]) -> str:
    data = json.dumps(candidates, ensure_ascii=False).replace("</", "<\\/")
    reasons = json.dumps(criteria.get("exclusion_reasons", []), ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(str(criteria.get("review_title") or "Literature screening queue"))
    return f"""<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{title}</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;margin:0 auto;max-width:900px;padding:24px;color:#111}}button,select,textarea{{font:inherit;margin:4px;padding:8px}}button{{cursor:pointer}}.include{{background:#d8f3dc}}.exclude{{background:#ffd6d6}}.fulltext{{background:#fff3bf}}.meta{{color:#555;font-size:.9em}}pre{{white-space:pre-wrap;background:#f6f6f6;padding:12px;border-radius:8px}}textarea{{display:block;width:100%;min-height:72px;box-sizing:border-box}}#counter{{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #ddd}}</style>
<body><h1>{title}</h1><p class=\"meta\">Local review helper. Decisions stay in this browser until you export them. Exported decisions require final human confirmation before synthesis.</p>
<div id=\"counter\"></div><main id=\"card\"></main><p><button onclick=\"download()\">Export reviewer_decisions.jsonl</button></p>
<script>
const records={data}; const reasons={reasons}; let index=0; const decisions={{}};
function esc(s){{const d=document.createElement('div');d.textContent=s||'';return d.innerHTML}}
function render(){{const r=records[index];document.querySelector('#counter').textContent=`${{index+1}} / ${{records.length}}`;document.querySelector('#card').innerHTML=`<h2>${{esc(r.record.title||'(untitled)')}}</h2><p class=meta>${{esc([r.record.authors,r.record.journal,r.record.year,r.record.pmid&&'PMID: '+r.record.pmid].filter(Boolean).join(' · '))}}</p><pre>${{esc(r.record.abstract||'No abstract available.')}}</pre><p><button class=include onclick=\"setDecision('include')\">Include</button><button class=fulltext onclick=\"setDecision('needs_fulltext')\">Needs full text</button><button class=exclude onclick=\"setDecision('exclude')\">Exclude</button></p><label>Exclusion reason <select id=reason><option value=\"\">—</option>${{reasons.map(x=>`<option value=\"${{esc(x.id)}}\">${{esc(x.label)}}</option>`).join('')}}</select></label><label>Reviewer note<textarea id=note placeholder=\"Brief title/abstract-grounded note\"></textarea></label><p><button onclick=\"previous()\">Previous</button><button onclick=\"next()\">Next</button></p>`; const d=decisions[r.record_id];if(d){{document.querySelector('#reason').value=d.exclusion_reason_id||'';document.querySelector('#note').value=d.rationale||'';}}}}
function setDecision(decision){{const r=records[index], reason=document.querySelector('#reason').value, note=document.querySelector('#note').value.trim(); if(decision==='exclude'&&!reason){{alert('Choose an exclusion reason.');return}} decisions[r.record_id]={{record_id:r.record_id,stage:'title_abstract',decision,exclusion_reason_id:decision==='exclude'?reason:'',rationale:note,confidence:'',reviewer_type:'human',reviewer_name:'',human_final:false,decided_at_utc:new Date().toISOString()}}; if(index<records.length-1){{index++;render()}}}}
function saveCurrent(){{const r=records[index],d=decisions[r.record_id];if(d)d.rationale=document.querySelector('#note').value.trim()}}
function next(){{saveCurrent();if(index<records.length-1){{index++;render()}}}} function previous(){{saveCurrent();if(index>0){{index--;render()}}}}
function download(){{saveCurrent();const text=Object.values(decisions).map(x=>JSON.stringify(x)).join('\\n')+'\\n';const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{{type:'application/x-ndjson'}}));a.download='reviewer_decisions.jsonl';a.click();URL.revokeObjectURL(a.href)}} render();
</script></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local, agent-friendly title/abstract screening queue.")
    parser.add_argument("records_json", type=Path, help="PubMed records.json from the search pipeline")
    parser.add_argument("screening_dir", type=Path, help="Directory for criteria, JSONL queue, and reviewer HTML")
    parser.add_argument("--criteria", type=Path, help="Existing screening_criteria.json; default is inside screening_dir")
    args = parser.parse_args()
    criteria_path = args.criteria or args.screening_dir / "screening_criteria.json"
    try:
        records = load_records(args.records_json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    args.screening_dir.mkdir(parents=True, exist_ok=True)
    if not criteria_path.exists():
        criteria_path.write_text(json.dumps(DEFAULT_CRITERIA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Created criteria template: {criteria_path.resolve()}")
        print("Fill in the review question and protocol-specific criteria, then rerun this command.", file=sys.stderr)
        return 3
    try:
        criteria = json.loads(criteria_path.read_text(encoding="utf-8-sig"))
        if not isinstance(criteria, dict) or not isinstance(criteria.get("inclusion_criteria"), list) or not isinstance(criteria.get("exclusion_reasons"), list):
            raise ValueError("criteria must contain inclusion_criteria and exclusion_reasons lists.")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Criteria error: {exc}", file=sys.stderr)
        return 2
    candidates = [queue_record(record, args.records_json) for record in records]
    queue_path = args.screening_dir / "screening_candidates.jsonl"
    queue_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in candidates), encoding="utf-8")
    (args.screening_dir / "agent_screening_instructions.md").write_text(DECISION_PROMPT, encoding="utf-8")
    (args.screening_dir / "review_queue.html").write_text(html_page(candidates, criteria), encoding="utf-8")
    manifest = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "source_records": str(args.records_json.resolve()), "criteria": str(criteria_path.resolve()), "candidate_count": len(candidates), "stage": "title_abstract"}
    (args.screening_dir / "screening_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(candidates)} screening candidates: {queue_path.resolve()}")
    print(f"Agent instructions: {(args.screening_dir / 'agent_screening_instructions.md').resolve()}")
    print(f"Human review helper: {(args.screening_dir / 'review_queue.html').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
