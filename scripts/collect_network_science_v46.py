from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.learner.autonomous_science_os_v46 import (
    AutonomousNetworkScoutV46,
    LiteratureKnowledgeAuditorV46,
    network_choice_commitment_v46,
)


BROKER = ROOT / "scripts/v46_network_reality_broker.py"
DESTINATION = ROOT / "data/network_v46/network_reality_v46_latest.json"


class BrokerClient:
    def __init__(self):
        self.process = subprocess.Popen(
            [sys.executable, "-B", str(BROKER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    def send(self, operation, **payload):
        self.process.stdin.write(json.dumps({"op": operation, **payload}, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(self.process.stderr.read())
        response = json.loads(line)
        if not response.get("ok"):
            raise RuntimeError(response)
        return response

    def close(self):
        self.send("shutdown")
        self.process.wait(timeout=10)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None:
                stream.close()


def main():
    v44 = json.loads((ROOT / "reports/data/autonomous_world_research_v44_latest.json").read_text(encoding="utf-8"))
    v45 = json.loads((ROOT / "reports/data/autonomous_intervention_v45_latest.json").read_text(encoding="utf-8"))
    queue = v44["acceptance"]["autonomous_agenda"]["next_research_queue"]
    client = BrokerClient()
    try:
        catalog = client.send("catalog")
        agenda = AutonomousNetworkScoutV46().choose(queue, catalog["sources"])
        selected = agenda["selected"]
        commitment = network_choice_commitment_v46(selected)
        committed = client.send(
            "commit_source", source_id=selected.source_id, commitment=commitment,
        )
        collection = client.send("collect", commitment=commitment)
        metadata = client.send("reveal_metadata")
        human = v45["acceptance"]["posthoc_translation"]["human_equivalent"]
        query = human + " computational complexity operation count nested loop conditional branch"
        literature_response = client.send("literature_search", query=query)
    finally:
        client.close()
    literature = LiteratureKnowledgeAuditorV46().audit(query, literature_response)
    payload = {
        "snapshot_version": "network-reality-v46.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dependencies": {"v44_run_id": v44["run_id"], "v45_run_id": v45["run_id"]},
        "network_policy": {
            "allowlisted_broker": True,
            "arbitrary_urls_allowed": catalog["arbitrary_urls_allowed"],
            "source_catalog_size": len(catalog["sources"]),
        },
        "autonomous_source_agenda": {
            "ranking": [item.to_dict() for item in agenda["ranked"]],
            "selected": selected.to_dict(),
            "host_selected": agenda["host_selected"],
        },
        "preregistration": {
            "source_commitment": commitment,
            "commit_event_index": committed["event_index"],
            "collection_event_index": collection["event_index"],
            "metadata_reveal_event_index": metadata["event_index"],
        },
        "anonymous_collection": {
            "source_id": collection["source_id"],
            "record_count": collection["record_count"],
            "records": collection["records"],
            "receipt": collection["receipt"],
            "domain_name_exposed_during_collection": collection["domain_name_exposed"],
        },
        "posthoc_source_metadata": metadata["metadata"],
        "literature_audit": literature,
    }
    payload["content_digest"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({
        "destination": str(DESTINATION),
        "selected_source": selected.source_id,
        "record_count": collection["record_count"],
        "network_sha256": collection["receipt"]["sha256"],
        "literature_records": literature["record_count"],
        "literature_status": literature["audit_status"],
        "content_digest": payload["content_digest"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
