#!/usr/bin/env python3
"""
run_pipeline.py — ONE entry point for the narrative-review-search skill.
Search terms in -> THREE Excels out: search log, evidence table, gap map.

Usage:
    python3 run_pipeline.py query.json outdir [--extraction extraction.json] [--auto]

query.json (drives the sweep AND the gap-map axes):
    question_type : "scoping"          (recommended for a sweep)
    population    : str (optional anchor)
    or_terms      : [str]  intervention/concept terms  <-- also used to auto-detect `contrast`
    outcome_terms : [str]  outcome domains to map      <-- used to auto-detect `domains` (gap-map columns)
    plus any filters (species, date_from/to, pub_types, max_results, ...). abstracts are forced ON.

Outputs (always 3 files in outdir):
    01_search_log.xlsx    raw identification pool (deterministic, objective)
    02_evidence_table.xlsx   design-aware evidence table   } from an extraction JSON
    03_gap_map.xlsx          contrast x domain gap map      }

Extraction JSON (the table/gap content):
    --extraction FILE : use a human/Claude-prepared extraction (paraphrased key_finding,
                        design, evidence_level, direction, conflict, contrast, domains, fields).
                        THIS is the proper path — extraction is reasoning, not regex.
    --auto            : if no extraction is given, build a DRAFT extraction from PubMed
                        metadata only: design from pub_type, contrast/domains auto-detected
                        from query terms, judgement columns left blank + verified=false.
                        Tables are stamped DRAFT and MUST be verified by a human.

The split is deliberate: the search log is objective; the evidence table and gap map
encode judgement. --auto gives you a scaffold so 3 files always appear, but the synthesis
columns are the reviewer's to complete. Do not present --auto output as finished.
"""
import sys, os, json, subprocess, argparse

HERE = os.path.dirname(os.path.abspath(__file__))

DESIGN_FROM_PUBTYPE = [  # ordered; first match wins
    ("randomized controlled trial", "RCT"), ("equivalence trial", "RCT"),
    ("meta-analysis", "Meta-analysis"), ("systematic review", "Systematic review"),
    ("observational study", "Cohort"), ("comparative study", "Cohort"),
    ("multicenter study", "Cohort"), ("case reports", "Case report"),
]
STUDY_DESIGNS = {"RCT","Cohort","Case-control","Cross-sectional","Case report",
                 "Case series","Systematic review","Meta-analysis"}

def design_from(pub_type):
    p = (pub_type or "").lower()
    for key, d in DESIGN_FROM_PUBTYPE:
        if key in p:
            return d
    return None  # background (review/guideline/editorial) -> excluded from evidence table

def run(script, *args):
    subprocess.run([sys.executable, os.path.join(HERE, script), *args], check=True)

def dedup(records):
    seen=set(); out=[]
    for r in records:
        k=r.get("pmid") or r.get("doi") or r.get("title","")
        if k in seen: continue
        seen.add(k); out.append(r)
    return out

def auto_extract(records, query):
    """DRAFT extraction from metadata only. Judgement columns BLANK; verified=false."""
    or_terms = [t.lower() for t in (query.get("or_terms") or [])]
    outcome_terms = query.get("outcome_terms") or []
    population = query.get("population","")
    studies=[]
    for r in records:
        design = design_from(r.get("publication_type"))
        if design not in STUDY_DESIGNS:
            continue  # leave reviews/guidelines out of the evidence table
        hay = (r.get("title","") + " " + r.get("abstract","")).lower()
        hits = [t for t in or_terms if t in hay]
        if "placebo" in hay and hits:
            contrast = f"{hits[0]} vs placebo"
        elif len(hits) >= 2:
            contrast = f"{hits[0]} vs {hits[1]}"
        elif len(hits) == 1:
            contrast = f"{hits[0]} (single-arm/unspecified)"
        else:
            contrast = "unclassified"
        domains = [d for d in outcome_terms if d.lower() in hay] or []
        first_author = (r.get("authors","").split(";")[0] or "?").strip()
        studies.append({
            "citation": f"{first_author} {r.get('year','')}".strip(),
            "pmid": r.get("pmid","NR"), "doi": r.get("doi","NR"),
            "verified": False,                       # metadata only; not human-checked
            "design": design, "population": population,
            "key_finding": "",                       # DRAFT: paraphrase from paper (human/Claude)
            "evidence_level": {"RCT":"High","Meta-analysis":"High","Systematic review":"High"}
                              .get(design,"Moderate" if design in ("Cohort","Case-control") else "Low"),
            "direction": "",                          # judgement
            "conflict": "",                           # judgement
            "synthesis_note": "",                     # judgement
            "contrast": contrast, "domains": domains,
            "fields": {}                              # fill from paper per design schema
        })
    return studies

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("query"); ap.add_argument("outdir")
    ap.add_argument("--extraction"); ap.add_argument("--auto", action="store_true")
    a=ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    query=json.load(open(a.query, encoding="utf-8-sig"))
    query["with_abstracts"]=True  # need abstracts for detection + screening

    # tmp query with abstracts on
    qpath=os.path.join(a.outdir,"_query.json")
    json.dump(query, open(qpath,"w",encoding="utf-8"), ensure_ascii=False)
    recs_path=os.path.join(a.outdir,"records.json")

    # ---- 1. SEARCH + SEARCH LOG (always) ----
    run("search.py","--query",qpath,"--out",recs_path)
    log_path=os.path.join(a.outdir,"01_search_log.xlsx")
    run("build_search_log.py",recs_path,log_path,
        "--label", query.get("population","") or "scoping sweep")

    records=dedup(json.load(open(recs_path,encoding="utf-8-sig")))

    # ---- 2. EXTRACTION (judgement) ----
    if a.extraction:
        extr_path=a.extraction
    else:
        if not a.auto:
            print("\nNo --extraction given. Re-run with --auto for a DRAFT table/gap, "
                  "or supply a prepared extraction.json (the proper path).")
            print(f"Search log written: {log_path}")
            return
        studies=auto_extract(records, query)
        extr_path=os.path.join(a.outdir,"extraction_DRAFT.json")
        json.dump(studies, open(extr_path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[--auto] DRAFT extraction: {len(studies)} study-type records "
              f"(judgement columns blank, verified=false) -> {extr_path}")

    # ---- 3. EVIDENCE TABLE + GAP MAP ----
    run("build_table.py", extr_path, os.path.join(a.outdir,"02_evidence_table.xlsx"))
    run("build_gap_map.py", extr_path, os.path.join(a.outdir,"03_gap_map.xlsx"))

    print("\nDONE. 3 Excels in", a.outdir)
    print("  01_search_log.xlsx     (objective: raw identification pool)")
    print("  02_evidence_table.xlsx (judgement: verify + paraphrase before use)")
    print("  03_gap_map.xlsx        (judgement: write the gap statements yourself)")

if __name__ == "__main__":
    main()
