"""Sealed subprocess broker for the NIST Pontius intervention snapshot."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: v38_intervention_broker.py SNAPSHOT.csv")
    path = Path(sys.argv[1]).resolve()
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    normalized = []
    for row in rows:
        payload = f"{row['run_index']}:{row['within_run_index']}:{row['load']}"
        normalized.append({
            "row_id": "INT-" + hashlib.sha256(payload.encode()).hexdigest()[:16],
            "batch": int(row["run_index"]),
            "level_index": int(row["within_run_index"]),
            "q0": float(row["load"]) / 3_000_000.0,
            "target": float(row["deflection"]),
        })
    train = [row for row in normalized if row["batch"] == 1 and row["level_index"] % 2 == 1]
    future = [row for row in normalized if row["batch"] == 2]
    committed = None
    event_index = 0
    for line in sys.stdin:
        request = json.loads(line)
        operation = request.get("op")
        if operation == "metadata":
            response = {
                "ok": True, "broker_pid": os.getpid(), "rows": len(rows),
                "training_rows": len(train), "future_rows": len(future),
                "controlled_slot": "Q0", "response_slot": "Q1",
                "experimental_batches": 2, "randomized_order": False,
                "training_levels": len({row["q0"] for row in train}),
                "future_unseen_levels": sum(row["q0"] not in {item["q0"] for item in train} for row in future),
            }
        elif operation == "training":
            response = {"ok": True, "rows": [{"row_id": row["row_id"], "q0": row["q0"], "target": row["target"]} for row in train]}
        elif operation == "future_inputs":
            response = {"ok": True, "rows": [{"row_id": row["row_id"], "q0": row["q0"], "unseen_intervention_level": row["q0"] not in {item["q0"] for item in train}} for row in future]}
        elif operation == "commit":
            if committed is not None:
                response = {"ok": False, "error": "commitment_already_exists"}
            else:
                committed = str(request["commitment"])
                response = {"ok": True, "commitment": committed, "event_index": event_index}
                event_index += 1
        elif operation == "future_outputs":
            if committed is None:
                response = {"ok": False, "error": "prediction_commitment_required"}
            else:
                response = {"ok": True, "commitment": committed, "event_index": event_index, "rows": [{"row_id": row["row_id"], "target": row["target"]} for row in future]}
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
