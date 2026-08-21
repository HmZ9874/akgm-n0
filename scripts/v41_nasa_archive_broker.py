"""Sealed broker for the official NASA V41 dynamic battery snapshot."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/nasa_v41/nasa_battery_dynamic_snapshot.json"
PROVENANCE = ROOT / "data/nasa_v41/nasa_battery_dynamic_provenance.json"


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    if _digest(SNAPSHOT) != provenance["snapshot_sha256"]:
        raise RuntimeError("NASA V41 snapshot digest mismatch")
    event_index = 0
    committed = None
    by_partition = {
        partition: [
            {"trace_id": trace["trace_id"], "samples": trace["samples"]}
            for trace in data["traces"] if trace["partition"] == partition
        ]
        for partition in ("training", "validation", "future_holdout", "cross_cell_replication")
    }
    for line in sys.stdin:
        request = json.loads(line)
        operation = request.get("op")
        if operation == "metadata":
            response = {
                "ok": True,
                "broker_pid": os.getpid(),
                "dataset_id": "NASA-PCOE-RANDOM-WALK-2-V41",
                "anonymous_channels": data["anonymous_channels"],
                "human_quantity_names_exposed_to_learner": False,
                "training_trace_count": len(by_partition["training"]),
                "validation_trace_count": len(by_partition["validation"]),
                "future_trace_count_hidden": True,
                "replication_cell_hidden": True,
                "historical_archive": True,
                "live_measurement": False,
            }
        elif operation in ("training", "validation"):
            response = {"ok": True, "event_index": event_index, "partition": operation, "traces": by_partition[operation]}
            event_index += 1
        elif operation == "commit_program":
            digest = str(request.get("commitment", ""))
            if committed is not None or len(digest) != 64:
                response = {"ok": False, "error": "invalid_or_duplicate_program_commitment"}
            else:
                committed = digest
                response = {"ok": True, "event_index": event_index, "commitment": digest}
                event_index += 1
        elif operation in ("future_holdout", "cross_cell_replication"):
            if committed is None:
                response = {"ok": False, "error": "program_commitment_required"}
            else:
                response = {"ok": True, "event_index": event_index, "partition": operation, "traces": by_partition[operation]}
                event_index += 1
        elif operation == "shutdown":
            print(json.dumps({"ok": True}), flush=True)
            return 0
        else:
            response = {"ok": False, "error": "unsupported_operation"}
        print(json.dumps(response, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
