#!/usr/bin/env python3
"""Build auditable PubMed searches and retrieve verifiable records."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable

VERSION = "2.0.0"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CROSSREF = "https://api.crossref.org/works/"
TOOL = "narrative-review-search"
NCBI_RESULT_LIMIT = 9999
SUMMARY_BATCH = 200
TRANSIENT_HTTP = {429, 500, 502, 503, 504}
ALLOWED_QUESTION_TYPES = {
    "therapy",
    "risk_factor",
    "diagnosis",
    "prognosis",
    "frequency",
    "scoping",
}
ALLOWED_PROFILES = {"broad", "precise", "legacy"}


def _load_env_file(explicit: str | None = None) -> str | None:
    """Load only NCBI credentials from a UTF-8/BOM-safe env file."""
    configured = explicit or os.environ.get("NARRATIVE_REVIEW_ENV")
    if not configured:
        return None
    candidates = [Path(configured)]

    for path in candidates:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in {"NCBI_EMAIL", "NCBI_API_KEY"} or os.environ.get(key):
                continue
            os.environ[key] = value.strip().strip('"').strip("'")
        return str(path)
    return None


def validate_ncbi_email(email: str | None) -> str:
    value = (email or "").strip()
    if (
        not value
        or "@" not in value
        or value.lower().endswith("@example.com")
        or value.lower() == "researcher@example.com"
    ):
        raise ValueError(
            "NCBI_EMAIL is required and must be a real contact email. "
            "Set it in the environment or pass --env-file."
        )
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value.strip()


def _validate_concept_list(value: Any, path: str) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{path}[{index}] must be an object")
        concept_id = _require_string(item.get("id"), f"{path}[{index}].id")
        _require_string(item.get("label"), f"{path}[{index}].label")
        if concept_id.casefold() in seen:
            raise ValueError(f"duplicate concept id: {concept_id}")
        seen.add(concept_id.casefold())
        for key in ("aliases", "mesh_terms"):
            terms = item.get(key, [])
            if not isinstance(terms, list) or any(
                not isinstance(term, str) or not term.strip() for term in terms
            ):
                raise ValueError(f"{path}[{index}].{key} must be a list of strings")


def validate_query(query: Any) -> list[str]:
    """Validate query structure and return non-fatal migration warnings."""
    if not isinstance(query, dict):
        raise ValueError("query.json must contain one JSON object")
    question_type = query.get("question_type")
    if question_type not in ALLOWED_QUESTION_TYPES:
        raise ValueError(
            "question_type must be one of: " + ", ".join(sorted(ALLOWED_QUESTION_TYPES))
        )
    schema_version = query.get("schema_version", 1)
    if schema_version not in (1, 2):
        raise ValueError("schema_version must be 1 or 2")
    profile = query.get("search_profile", "broad")
    if profile not in ALLOWED_PROFILES:
        raise ValueError("search_profile must be broad, precise, or legacy")
    _validate_concept_list(query.get("concepts"), "concepts")
    _validate_concept_list(query.get("outcomes"), "outcomes")
    for key in (
        "or_terms",
        "outcome_terms",
        "and_terms",
        "not_terms",
        "mesh_terms",
        "pub_types",
    ):
        value = query.get(key)
        if value is not None and (
            not isinstance(value, list)
            or any(not isinstance(term, str) or not term.strip() for term in value)
        ):
            raise ValueError(f"{key} must be a list of non-empty strings")
    if "max_results" in query:
        value = query["max_results"]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("max_results must be a positive integer")
        if value > NCBI_RESULT_LIMIT:
            raise ValueError(
                f"PubMed can expose at most {NCBI_RESULT_LIMIT} results through ESearch; "
                "partition the query by date."
            )
    if query.get("doi_backfill", "validated") not in {"validated", "off"}:
        raise ValueError("doi_backfill must be validated or off")

    if question_type == "scoping" and not (
        query.get("concepts")
        or query.get("or_terms")
        or query.get("and_terms")
        or query.get("mesh_terms")
    ):
        raise ValueError(
            "scoping needs concepts or at least one of or_terms/and_terms/mesh_terms"
        )

    required_by_type = {
        "therapy": ("population", "intervention"),
        "risk_factor": ("population", "exposure", "outcome"),
        "diagnosis": ("population", "index_test", "target_condition"),
        "prognosis": ("condition", "outcome"),
        "frequency": ("condition",),
    }
    for field in required_by_type.get(question_type, ()):
        if not query.get(field) and not (
            field in {"intervention", "exposure", "index_test"}
            and query.get("concepts")
        ):
            raise ValueError(f"{question_type} requires {field}")

    warnings: list[str] = []
    if query.get("or_terms") and not query.get("concepts"):
        warnings.append(
            "Legacy or_terms are treated as separate concepts where applicable; "
            "use concepts[] to group aliases."
        )
    if query.get("outcome_terms") and not query.get("outcomes"):
        warnings.append(
            "Legacy outcome_terms remain supported; use outcomes[] to group aliases."
        )
    return warnings


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "concept"


def query_concepts(query: dict[str, Any]) -> list[dict[str, Any]]:
    if query.get("concepts"):
        return [
            {
                "id": item["id"].strip(),
                "label": item["label"].strip(),
                "aliases": [term.strip() for term in item.get("aliases", [])],
                "mesh_terms": [term.strip() for term in item.get("mesh_terms", [])],
            }
            for item in query["concepts"]
        ]
    question_type = query.get("question_type")
    if question_type == "scoping":
        terms = query.get("or_terms") or []
    else:
        field = {
            "therapy": "intervention",
            "risk_factor": "exposure",
            "diagnosis": "index_test",
            "prognosis": "predictor",
            "frequency": "condition",
        }.get(question_type)
        terms = [query[field]] if field and query.get(field) else []
    used: set[str] = set()
    concepts = []
    for term in terms:
        base = _slug(term)
        concept_id = base
        suffix = 2
        while concept_id in used:
            concept_id = f"{base}-{suffix}"
            suffix += 1
        used.add(concept_id)
        concepts.append(
            {"id": concept_id, "label": term.strip(), "aliases": [], "mesh_terms": []}
        )
    return concepts


def query_outcomes(query: dict[str, Any]) -> list[dict[str, Any]]:
    if query.get("outcomes"):
        return [
            {
                "id": item["id"].strip(),
                "label": item["label"].strip(),
                "aliases": [term.strip() for term in item.get("aliases", [])],
                "mesh_terms": [term.strip() for term in item.get("mesh_terms", [])],
            }
            for item in query["outcomes"]
        ]
    terms = query.get("outcome_terms") or (
        [query["outcome"]] if query.get("outcome") else []
    )
    return [
        {"id": _slug(term), "label": term.strip(), "aliases": [], "mesh_terms": []}
        for term in terms
    ]


def _clean_term(term: str) -> str:
    cleaned = re.sub(r"\s+", " ", term.replace('"', " ")).strip()
    if not cleaned:
        raise ValueError("search terms cannot be empty")
    return cleaned


def _atm_term(term: str) -> str:
    """Leave unstructured terms unquoted so PubMed ATM remains available."""
    return _clean_term(term)


def _tagged_term(term: str, tag: str) -> str:
    cleaned = _clean_term(term)
    rendered = f'"{cleaned}"' if " " in cleaned else cleaned
    return f"{rendered}[{tag}]"


def _concept_block(concepts: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    seen: set[str] = set()
    for concept in concepts:
        for term in [concept["label"], *concept.get("aliases", [])]:
            value = _tagged_term(term, "Title/Abstract")
            if value.casefold() not in seen:
                rendered.append(value)
                seen.add(value.casefold())
        for term in concept.get("mesh_terms", []):
            value = _tagged_term(term, "MeSH Terms")
            if value.casefold() not in seen:
                rendered.append(value)
                seen.add(value.casefold())
    return "(" + " OR ".join(rendered) + ")" if rendered else ""


def _or_block(terms: list[str], tagged: bool = False) -> str:
    if not terms:
        return ""
    values = [
        _tagged_term(term, "Title/Abstract") if tagged else _atm_term(term)
        for term in terms
    ]
    return "(" + " OR ".join(values) + ")"


def _dedupe_parts(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        key = part.casefold()
        if key not in seen:
            seen.add(key)
            out.append(part)
    return out


def _apply_filters(query: str, q: dict[str, Any]) -> str:
    filters: list[str] = []
    if q.get("date_from") or q.get("date_to"):
        lo = q.get("date_from", "1800")
        hi = q.get("date_to", "3000")
        filters.append(f'("{lo}"[Date - Publication] : "{hi}"[Date - Publication])')
    species = str(q.get("species", "")).casefold()
    if species.startswith("human"):
        filters.append("humans[MeSH Terms]")
    elif species.startswith("animal"):
        filters.append("animals[MeSH Terms]")
    if q.get("language"):
        filters.append(f'{_clean_term(str(q["language"]))}[Language]')
    for publication_type in q.get("pub_types", []) or []:
        filters.append(f'{_tagged_term(publication_type, "Publication Type")}')
    if filters:
        query = " AND ".join([query, *filters]) if query else " AND ".join(filters)
    for term in q.get("not_terms", []) or []:
        query += f" NOT {_atm_term(term)}"
    return query


def _legacy_group(term: str) -> str:
    cleaned = _clean_term(term)
    return f'"{cleaned}"' if " " in cleaned else cleaned


def _legacy_build_query(q: dict[str, Any]) -> str:
    question_type = q["question_type"]
    parts: list[str] = []

    def add(value: Any) -> None:
        if value:
            parts.append(_legacy_group(str(value)))

    add(q.get("population"))
    if question_type == "therapy":
        add(q.get("intervention"))
        add(q.get("comparator"))
        add(q.get("outcome"))
    elif question_type == "risk_factor":
        add(q.get("exposure"))
        add(q.get("comparator"))
        add(q.get("outcome"))
    elif question_type == "diagnosis":
        add(q.get("index_test"))
        add(q.get("target_condition"))
        add(q.get("reference_standard"))
        parts.append("(sensitivity OR specificity OR accuracy OR diagnostic)")
    elif question_type == "prognosis":
        add(q.get("condition"))
        add(q.get("outcome"))
        add(q.get("predictor"))
        add(q.get("timeframe"))
        parts.append("(prognosis OR survival OR mortality OR recurrence OR outcome)")
    elif question_type == "frequency":
        add(q.get("condition"))
        add(q.get("setting"))
        add(q.get("timeframe"))
        parts.append("(prevalence OR incidence OR epidemiology)")
    for term in q.get("mesh_terms", []) or []:
        parts.append(f"{_legacy_group(term)}[MeSH Terms]")
    for term in q.get("and_terms", []) or []:
        parts.append(_legacy_group(term))
    if q.get("or_terms"):
        parts.append("(" + " OR ".join(_legacy_group(t) for t in q["or_terms"]) + ")")
    return _apply_filters(" AND ".join(_dedupe_parts(parts)), q)


def build_query(q: dict[str, Any]) -> str:
    validate_query(q)
    profile = q.get("search_profile", "broad")
    if profile == "legacy":
        return _legacy_build_query(q)

    question_type = q["question_type"]
    concepts = query_concepts(q)
    parts: list[str] = []

    if question_type == "scoping":
        if q.get("population"):
            parts.append(_atm_term(q["population"]))
        if concepts:
            parts.append(_concept_block(concepts))
        elif q.get("or_terms"):
            parts.append(_or_block(q["or_terms"], tagged=True))
    elif question_type == "therapy":
        parts.append(_atm_term(q["population"]))
        parts.append(
            _concept_block(concepts)
            if q.get("concepts")
            else _atm_term(q["intervention"])
        )
    elif question_type == "risk_factor":
        parts.append(_atm_term(q["population"]))
        parts.append(
            _concept_block(concepts)
            if q.get("concepts")
            else _atm_term(q["exposure"])
        )
    elif question_type == "diagnosis":
        parts.extend(
            [_atm_term(q["target_condition"]), _atm_term(q["population"])]
        )
        parts.append(
            _concept_block(concepts)
            if q.get("concepts")
            else _atm_term(q["index_test"])
        )
        parts.append(
            "(sensitivity[Title/Abstract] OR specificity[Title/Abstract] "
            "OR accuracy[Title/Abstract] OR diagnostic[Title/Abstract])"
        )
    elif question_type == "prognosis":
        parts.append(_atm_term(q.get("condition") or q.get("population")))
        if q.get("predictor"):
            parts.append(_atm_term(q["predictor"]))
        else:
            parts.append(_atm_term(q["outcome"]))
        parts.append(
            "(prognosis[Title/Abstract] OR survival[Title/Abstract] "
            "OR mortality[Title/Abstract] OR recurrence[Title/Abstract])"
        )
    elif question_type == "frequency":
        parts.append(_atm_term(q.get("condition") or q.get("population")))
        parts.append(
            "(prevalence[Title/Abstract] OR incidence[Title/Abstract] "
            "OR epidemiology[Title/Abstract])"
        )

    for term in q.get("mesh_terms", []) or []:
        parts.append(_tagged_term(term, "MeSH Terms"))
    for term in q.get("and_terms", []) or []:
        parts.append(_atm_term(term))
    if question_type != "scoping" and q.get("or_terms"):
        parts.append(_or_block(q["or_terms"], tagged=True))

    if profile == "precise":
        precise_fields = {
            "therapy": ("comparator", "outcome"),
            "risk_factor": ("comparator", "outcome"),
            "diagnosis": ("reference_standard",),
            "prognosis": ("outcome", "timeframe"),
            "frequency": ("setting", "timeframe"),
        }
        for field in precise_fields.get(question_type, ()):
            if q.get(field):
                parts.append(_atm_term(str(q[field])))
        if q.get("outcomes"):
            parts.append(_concept_block(query_outcomes(q)))

    return _apply_filters(" AND ".join(_dedupe_parts(parts)), q)


class EUtilsClient:
    def __init__(
        self,
        email: str,
        api_key: str | None = None,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.email = validate_ncbi_email(email)
        self.api_key = api_key
        self.opener = opener
        self.sleeper = sleeper
        self.min_interval = 0.11 if api_key else 0.34
        self.last_request = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self.last_request
        if elapsed < self.min_interval:
            self.sleeper(self.min_interval - elapsed)
        self.last_request = time.monotonic()

    def request(self, endpoint: str, params: dict[str, Any], post: bool = False) -> bytes:
        payload = {**params, "tool": TOOL, "email": self.email}
        if self.api_key:
            payload["api_key"] = self.api_key
        encoded = urllib.parse.urlencode(payload).encode("utf-8")
        if post:
            request = urllib.request.Request(
                EUTILS + endpoint,
                data=encoded,
                headers={"User-Agent": f"{TOOL}/{VERSION} (mailto:{self.email})"},
            )
        else:
            request = urllib.request.Request(
                EUTILS + endpoint + "?" + encoded.decode("ascii"),
                headers={"User-Agent": f"{TOOL}/{VERSION} (mailto:{self.email})"},
            )

        for attempt in range(4):
            self._throttle()
            try:
                with self.opener(request, timeout=60) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                if exc.code not in TRANSIENT_HTTP or attempt == 3:
                    raise
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                delay = float(retry_after) if retry_after else 2**attempt
            except (urllib.error.URLError, TimeoutError):
                if attempt == 3:
                    raise
                delay = 2**attempt
            self.sleeper(min(delay, 60))
        raise RuntimeError("unreachable retry state")


def suggest_mesh(concept: str, client: EUtilsClient) -> list[str]:
    data = json.loads(
        client.request(
            "esearch.fcgi",
            {"db": "mesh", "term": concept, "retmax": "5", "retmode": "json"},
        )
    )
    ids = data["esearchresult"]["idlist"]
    if not ids:
        return []
    summary = json.loads(
        client.request(
            "esummary.fcgi",
            {"db": "mesh", "id": ",".join(ids), "retmode": "json"},
        )
    )["result"]
    out: list[str] = []
    for uid in summary.get("uids", []):
        name = summary[uid].get("ds_meshterms") or summary[uid].get("title")
        if isinstance(name, list):
            name = name[0] if name else None
        if name:
            out.append(name)
    return out


def _parse_pubmed_xml(payload: bytes) -> dict[str, tuple[str, str]]:
    root = ET.fromstring(payload)
    records: dict[str, tuple[str, str]] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_element = article.find("./MedlineCitation/PMID")
        pmid = pmid_element.text if pmid_element is not None else None
        if not pmid:
            continue
        abstract_parts: list[str] = []
        for element in article.findall("./MedlineCitation/Article/Abstract/AbstractText"):
            label = element.get("Label")
            text = "".join(element.itertext()).strip()
            if text:
                abstract_parts.append(f"{label}: {text}" if label else text)
        mesh = "; ".join(
            element.text
            for element in article.findall(
                "./MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName"
            )
            if element.text
        )
        records[pmid] = (" ".join(abstract_parts).strip(), mesh)
    return records


def _normalise_title(title: str) -> str:
    value = unicodedata.normalize("NFKC", title).casefold()
    return re.sub(r"[^a-z0-9]+", "", value)


def _crossref_year(item: dict[str, Any]) -> str:
    for key in (
        "published-print",
        "published-online",
        "published",
        "issued",
        "created",
    ):
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            return str(parts[0][0])
    return ""


def crossref_doi(
    title: str,
    year: str,
    policy: str = "validated",
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> tuple[str, str, float | None]:
    if policy == "off" or not title:
        return "NR", "missing", None
    url = CROSSREF + "?" + urllib.parse.urlencode(
        {"query.bibliographic": title, "rows": "3"}
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": f"{TOOL}/{VERSION} (https://www.ncbi.nlm.nih.gov/)"}
    )
    try:
        with opener(request, timeout=60) as response:
            items = json.loads(response.read()).get("message", {}).get("items", [])
    except (OSError, ValueError, urllib.error.URLError):
        return "NR", "missing", None
    expected = _normalise_title(title)
    for item in items:
        candidate_titles = item.get("title") or []
        candidate = candidate_titles[0] if candidate_titles else ""
        if (
            expected
            and _normalise_title(candidate) == expected
            and _crossref_year(item) == str(year)
            and item.get("DOI")
        ):
            return str(item["DOI"]), "crossref_validated", 1.0
    return "NR", "missing", None


def run_search(
    query_config: dict[str, Any],
    client: EUtilsClient,
    crossref_lookup: Callable[
        [str, str, str], tuple[str, str, float | None]
    ] = crossref_doi,
) -> dict[str, Any]:
    warnings = validate_query(query_config)
    query = build_query(query_config)
    sort = query_config.get("sort") or (
        "relevance" if query_config["question_type"] == "scoping" else "default"
    )
    search_params: dict[str, Any] = {
        "db": "pubmed",
        "term": query,
        "retmax": "0",
        "retmode": "json",
        "usehistory": "y",
    }
    if sort != "default":
        search_params["sort"] = sort
    search_result = json.loads(
        client.request("esearch.fcgi", search_params)
    )["esearchresult"]
    count = int(search_result["count"])
    query_translation = search_result.get("querytranslation", "")
    target = query_config.get("max_results", count)
    if "max_results" not in query_config and count > NCBI_RESULT_LIMIT:
        raise ValueError(
            f"PubMed returned {count} hits, above the {NCBI_RESULT_LIMIT}-record "
            "ESearch limit. Partition the query by date or set an explicit max_results."
        )
    target = min(int(target), count)
    if target > NCBI_RESULT_LIMIT:
        raise ValueError(
            f"Cannot retrieve more than {NCBI_RESULT_LIMIT} PubMed records in one run"
        )
    if target < count:
        warnings.append(
            f"PARTIAL retrieval: {target} of {count} hits were requested."
        )

    records: list[dict[str, Any]] = []
    if target:
        webenv = search_result.get("webenv")
        query_key = search_result.get("querykey")
        if not webenv or not query_key:
            raise RuntimeError("NCBI did not return WebEnv/query_key for history retrieval")
        for retstart in range(0, target, SUMMARY_BATCH):
            batch_size = min(SUMMARY_BATCH, target - retstart)
            history = {
                "db": "pubmed",
                "query_key": query_key,
                "WebEnv": webenv,
                "retstart": str(retstart),
                "retmax": str(batch_size),
            }
            summary_result = json.loads(
                client.request(
                    "esummary.fcgi",
                    {**history, "retmode": "json"},
                    post=batch_size >= SUMMARY_BATCH,
                )
            )["result"]
            uids = summary_result.get("uids", [])
            if len(uids) != batch_size:
                raise RuntimeError(
                    f"Incomplete ESummary batch at {retstart}: "
                    f"expected {batch_size}, received {len(uids)}"
                )
            fetched = _parse_pubmed_xml(
                client.request(
                    "efetch.fcgi",
                    {**history, "retmode": "xml"},
                    post=batch_size >= SUMMARY_BATCH,
                )
            )
            missing = [uid for uid in uids if uid not in fetched]
            if missing:
                raise RuntimeError(
                    "Incomplete EFetch batch; missing PubMed records: "
                    + ", ".join(missing[:10])
                )
            for uid in uids:
                summary = summary_result[uid]
                title = str(summary.get("title", "")).rstrip(".")
                year = str(summary.get("pubdate", "") or "")[:4]
                article_ids = summary.get("articleids", [])
                doi = next(
                    (
                        item.get("value")
                        for item in article_ids
                        if item.get("idtype") == "doi" and item.get("value")
                    ),
                    "NR",
                )
                doi_source = "pubmed" if doi != "NR" else "missing"
                confidence: float | None = 1.0 if doi != "NR" else None
                if doi == "NR":
                    doi, doi_source, confidence = crossref_lookup(
                        title, year, query_config.get("doi_backfill", "validated")
                    )
                authors = "; ".join(
                    item.get("name", "")
                    for item in summary.get("authors", [])[:6]
                    if item.get("name")
                )
                if len(summary.get("authors", [])) > 6:
                    authors += " et al."
                abstract, mesh = fetched[uid]
                records.append(
                    {
                        "pmid": uid,
                        "doi": doi,
                        "doi_source": doi_source,
                        "doi_match_confidence": confidence,
                        "title": title,
                        "authors": authors,
                        "journal": summary.get("source", ""),
                        "year": year,
                        "abstract": abstract,
                        "publication_type": ", ".join(summary.get("pubtype", [])),
                        "mesh": mesh,
                    }
                )

    return {
        "query": query,
        "query_translation": query_translation,
        "count": count,
        "returned": len(records),
        "complete": len(records) == count,
        "retrieval_status": "COMPLETE" if len(records) == count else "PARTIAL",
        "sort": sort,
        "warnings": warnings,
        "records": records,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suggest-mesh")
    parser.add_argument("--query")
    parser.add_argument("--out")
    parser.add_argument("--show-query", action="store_true")
    parser.add_argument("--env-file")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args()

    if not args.query and not args.suggest_mesh:
        parser.print_help()
        return

    if args.query:
        query_path = Path(args.query)
        query_config = json.loads(query_path.read_text(encoding="utf-8-sig"))
        warnings = validate_query(query_config)
        if args.show_query:
            print(build_query(query_config))
            for warning in warnings:
                print(f"WARNING: {warning}", file=sys.stderr)
            return

    _load_env_file(args.env_file)
    client = EUtilsClient(
        validate_ncbi_email(os.environ.get("NCBI_EMAIL")),
        os.environ.get("NCBI_API_KEY"),
    )
    if args.suggest_mesh:
        print(
            json.dumps(
                suggest_mesh(args.suggest_mesh, client),
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    result = run_search(query_config, client)
    output = Path(args.out or "results.json")
    retrieved_utc = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    _write_json(output, result["records"])
    metadata = {
        key: result[key]
        for key in (
            "query",
            "query_translation",
            "count",
            "returned",
            "complete",
            "retrieval_status",
            "sort",
            "warnings",
        )
    }
    metadata.update(
        {
            "database": "PubMed",
            "platform": "NCBI E-utilities",
            "retrieved_utc": retrieved_utc,
            "skill_version": VERSION,
            "search_profile": query_config.get("search_profile", "broad"),
            "doi_backfill": query_config.get("doi_backfill", "validated"),
        }
    )
    _write_json(Path(str(output) + ".meta.json"), metadata)
    manifest = {
        **metadata,
        "schema_version": query_config.get("schema_version", 1),
        "original_query": query_config,
        "records_file": output.name,
        "credentials_logged": False,
    }
    _write_json(output.parent / "run_manifest.json", manifest)
    print(f"Query: {result['query']}")
    print(
        f"Sort: {result['sort']} | Total hits: {result['count']} | "
        f"retrieved: {result['returned']} ({result['retrieval_status']}) -> {output}"
    )
    for warning in result["warnings"]:
        print(f"WARNING: {warning}", file=sys.stderr)


if __name__ == "__main__":
    main()
