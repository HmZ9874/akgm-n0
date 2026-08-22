from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.learner.full_text_literature_research_v47 import (
    AutonomousLiteraturePlannerV47,
    FrozenDiscoveryV47,
    FullTextPriorArtAuditorV47,
    canonical_digest,
)


class BrokerClient:
    def __init__(self):
        self.process = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts/v47_open_literature_broker.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    def send(self, op, **payload):
        assert self.process.stdin is not None and self.process.stdout is not None
        self.process.stdin.write(json.dumps({"op": op, **payload}) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            error = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError("literature broker stopped: " + error)
        response = json.loads(line)
        if not response.get("ok"):
            raise RuntimeError(response)
        return response

    def close(self):
        try:
            self.send("shutdown")
        finally:
            self.process.wait(timeout=10)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    v46 = _load(ROOT / "reports/data/autonomous_science_os_v46_latest.json")
    semantic = v46["acceptance"]["open_language_creation"]["invented_semantic"]
    discovery = FrozenDiscoveryV47(
        semantic["semantic_id"],
        tuple(semantic["expansion_features"]),
        tuple(map(float, semantic["expansion_coefficients"])),
        v46["content_digest"],
    )
    planner = AutonomousLiteraturePlannerV47()
    plan = planner.plan(discovery)
    broker = BrokerClient()
    try:
        catalog = broker.send("catalog")
        commitment = broker.send("commit_discovery", commitment=discovery.commitment)
        searches = [
            broker.send("search", query_id=item["query_id"])
            for item in plan["selected_queries"]
        ]
        selection = FullTextPriorArtAuditorV47().rank_metadata(searches, limit=6)
        documents = [
            broker.send("full_text", pmcid=item["pmcid"])
            for item in selection["selected"]
        ]
    finally:
        broker.close()
    now = datetime.now(timezone.utc)
    request_count = len(searches) + len(documents)
    payload = {
        "snapshot_version": "open-literature-evidence-v47.0",
        "created_at": now.isoformat(),
        "provider": catalog["provider"],
        "policy": {
            "allowlisted_root": catalog["allowlisted_root"],
            "arbitrary_queries_allowed": catalog["arbitrary_queries_allowed"],
            "arbitrary_urls_allowed": catalog["arbitrary_urls_allowed"],
            "full_text_retained": False,
        },
        "frozen_discovery": discovery.payload(),
        "preregistration": {
            "discovery_commitment": discovery.commitment,
            "commit_event_index": commitment["event_index"],
            "first_search_event_index": min(item["event_index"] for item in searches),
            "first_full_text_event_index": min(item["event_index"] for item in documents),
        },
        "autonomous_query_plan": plan,
        "metadata_searches": searches,
        "autonomous_document_selection": selection,
        "full_text_documents": documents,
        "request_count": request_count,
        "metadata_record_count": sum(len(item["records"]) for item in searches),
    }
    payload["content_digest"] = canonical_digest(payload)
    destination = ROOT / "data/network_v47/open_literature_evidence_v47_latest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "collected",
        "provider": payload["provider"],
        "search_count": len(searches),
        "metadata_records": payload["metadata_record_count"],
        "full_text_documents": len(documents),
        "network_requests": request_count,
        "selected_pmcids": [item["pmcid"] for item in documents],
        "content_digest": payload["content_digest"],
        "path": str(destination.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
