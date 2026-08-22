"""Isolated allowlisted Europe PMC broker for the V47 audit.

The broker never returns whole article text.  It returns metadata, source
digests, licence evidence, word counts, and deterministic concept counts.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


USER_AGENT = "AKGM-N0/0.47 (open-literature-audit; public GitHub project)"
API_ROOT = "https://www.ebi.ac.uk/europepmc/webservices/rest/"

QUERY_CATALOG = {
    "Q-STRUCTURE-SEARCH": 'TITLE_ABS:"symbolic regression" AND OPEN_ACCESS:Y sort_cited:y',
    "Q-REUSABLE-SEMANTIC": '"automatically defined functions" AND OPEN_ACCESS:Y sort_cited:y',
    "Q-GUARDED-FORM": '("piecewise function" AND "symbolic regression") AND OPEN_ACCESS:Y sort_cited:y',
    "Q-PARSIMONY": '("parsimony" AND "symbolic regression") AND OPEN_ACCESS:Y sort_cited:y',
}

SIGNATURES = {
    "structure_search": (
        "symbolic regression", "genetic programming", "program synthesis",
        "expression tree", "search space",
    ),
    "reusable_semantic": (
        "automatically defined function", "subroutine", "reusable",
        "modular", "module", "macro",
    ),
    "guarded_form": (
        "piecewise function", "conditional", "if-then", "if then", "guard",
        "branch",
    ),
    "interaction_product": (
        "interaction term", "product term", "multiplication", "multivariate",
        "epistasis",
    ),
    "parsimony": (
        "parsimony", "complexity", "program size", "description length",
        "simplification", "compression",
    ),
    "verification": (
        "holdout", "cross-validation", "cross validation", "benchmark",
        "generalization", "falsification",
    ),
}


def _download(url):
    if not url.startswith(API_ROOT):
        raise ValueError("host_not_allowlisted")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.time_ns()
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
        status = response.status
        content_type = response.headers.get("Content-Type")
    ended = time.time_ns()
    if not payload:
        raise RuntimeError("empty_official_response")
    return payload, {
        "url": url,
        "status": status,
        "content_type": content_type,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "started_at_unix_ns": started,
        "ended_at_unix_ns": ended,
    }


def _search(query_id):
    query = QUERY_CATALOG[query_id]
    url = API_ROOT + "search?" + urllib.parse.urlencode({
        "query": query,
        "format": "json",
        "pageSize": "15",
        "resultType": "core",
    })
    raw, receipt = _download(url)
    payload = json.loads(raw)
    records = []
    for item in payload.get("resultList", {}).get("result", ()):
        records.append({
            "pmcid": item.get("pmcid"),
            "doi": item.get("doi"),
            "title": item.get("title"),
            "journal": item.get("journalTitle"),
            "publication_year": item.get("pubYear"),
            "cited_by_count": int(item.get("citedByCount") or 0),
            "is_open_access": item.get("isOpenAccess") == "Y",
            "author_string": item.get("authorString"),
        })
    return {
        "query_id": query_id,
        "query": query,
        "hit_count": int(payload.get("hitCount") or 0),
        "records": records,
        "receipt": receipt,
    }


def _node_text(node):
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def _full_text(pmcid):
    if not re.fullmatch(r"PMC[0-9]+", pmcid):
        raise ValueError("invalid_pmcid")
    url = API_ROOT + pmcid + "/fullTextXML"
    raw, receipt = _download(url)
    root = ET.fromstring(raw)
    title = _node_text(root.find(".//article-title"))
    body = root.find(".//body")
    body_text = _node_text(body).lower()
    licence_ref = root.find(".//{http://www.niso.org/schemas/ali/1.0/}license_ref")
    licence_url = _node_text(licence_ref) or None
    if not licence_url:
        external = root.find(".//permissions/license//ext-link")
        if external is not None:
            licence_url = external.attrib.get("{http://www.w3.org/1999/xlink}href")
    sections = []
    for section in root.findall(".//body/sec"):
        heading = _node_text(section.find("title"))
        if heading and heading not in sections:
            sections.append(heading[:100])
    counts = {
        dimension: sum(body_text.count(phrase) for phrase in phrases)
        for dimension, phrases in SIGNATURES.items()
    }
    matched = {
        dimension: [phrase for phrase in phrases if phrase in body_text]
        for dimension, phrases in SIGNATURES.items()
    }
    return {
        "pmcid": pmcid,
        "title": title,
        "full_text_retrieved": True,
        "open_licence_detected": bool(licence_url),
        "licence_url": licence_url,
        "body_word_count": len(body_text.split()),
        "section_headings": sections[:20],
        "signature_counts": counts,
        "matched_phrases": matched,
        "full_text_stored_in_repository": False,
        "receipt": receipt,
    }


def main():
    searched_pmcids = set()
    committed_discovery = None
    event_index = 0
    for line in sys.stdin:
        request = json.loads(line)
        operation = request.get("op")
        try:
            if operation == "catalog":
                response = {
                    "ok": True,
                    "provider": "Europe PMC REST API",
                    "query_catalog": [
                        {"query_id": key, "query": value}
                        for key, value in QUERY_CATALOG.items()
                    ],
                    "allowlisted_root": API_ROOT,
                    "arbitrary_queries_allowed": False,
                    "arbitrary_urls_allowed": False,
                }
            elif operation == "commit_discovery":
                digest = str(request.get("commitment", ""))
                if committed_discovery is not None or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    response = {"ok": False, "error": "invalid_or_duplicate_discovery_commitment"}
                else:
                    committed_discovery = digest
                    response = {"ok": True, "event_index": event_index, "commitment": digest}
                    event_index += 1
            elif operation == "search":
                query_id = str(request.get("query_id", ""))
                if committed_discovery is None:
                    response = {"ok": False, "error": "discovery_commitment_required"}
                elif query_id not in QUERY_CATALOG:
                    response = {"ok": False, "error": "query_not_allowlisted"}
                else:
                    result = _search(query_id)
                    searched_pmcids.update(
                        item["pmcid"] for item in result["records"] if item["pmcid"]
                    )
                    response = {"ok": True, "event_index": event_index, **result}
                    event_index += 1
            elif operation == "full_text":
                pmcid = str(request.get("pmcid", ""))
                if pmcid not in searched_pmcids:
                    response = {"ok": False, "error": "pmcid_must_come_from_search"}
                else:
                    response = {"ok": True, "event_index": event_index, **_full_text(pmcid)}
                    event_index += 1
            elif operation == "shutdown":
                print(json.dumps({"ok": True}), flush=True)
                return 0
            else:
                response = {"ok": False, "error": "unsupported_operation"}
        except Exception as error:
            response = {"ok": False, "error": type(error).__name__, "message": str(error)}
        print(json.dumps(response, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
