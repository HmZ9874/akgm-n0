"""JSON-lines subprocess broker for the sealed V37 real-data snapshot."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path


def _number(value):
    return None if value in (None, "") else float(value)


def _uncertainty(row, positive, negative):
    values = [abs(value) for value in (_number(row[positive]), _number(row[negative])) if value is not None]
    return None if not values else sum(values) / len(values)


def _load(path: Path):
    result = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            digest = hashlib.sha256(row["pl_name"].encode()).hexdigest()
            result.append({
                "row_id": "OBS-" + digest[:16],
                "q0": float(row["pl_orbsmax"]),
                "q1": float(row["st_mass"]),
                "target": float(row["pl_orbper"]),
                "sigma_q0": _uncertainty(row, "pl_orbsmaxerr1", "pl_orbsmaxerr2"),
                "sigma_q1": _uncertainty(row, "st_masserr1", "st_masserr2"),
                "sigma_target": _uncertainty(row, "pl_orbpererr1", "pl_orbpererr2"),
                "split": "holdout" if int(digest[:8], 16) % 5 == 0 else "train",
            })
    return result


def _inputs(row):
    return {key: row[key] for key in ("row_id", "q0", "q1", "sigma_q0", "sigma_q1")}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: v37_observation_broker.py SNAPSHOT.csv")
    path = Path(sys.argv[1]).resolve()
    rows = _load(path)
    train = [row for row in rows if row["split"] == "train"]
    holdout = [row for row in rows if row["split"] == "holdout"]
    committed = None
    event_index = 0
    for line in sys.stdin:
        request = json.loads(line)
        operation = request.get("op")
        if operation == "metadata":
            response = {"ok": True, "broker_pid": os.getpid(), "rows": len(rows), "train_rows": len(train), "holdout_rows": len(holdout), "anonymous_units": {"q0": "U0", "q1": "U1", "target": "U2"}}
        elif operation == "train":
            response = {"ok": True, "rows": [{**_inputs(row), "target": row["target"], "sigma_target": row["sigma_target"]} for row in train]}
        elif operation == "holdout_inputs":
            response = {"ok": True, "rows": [_inputs(row) for row in holdout]}
        elif operation == "commit":
            if committed is not None:
                response = {"ok": False, "error": "commitment_already_exists"}
            else:
                committed = str(request["commitment"])
                response = {"ok": True, "commitment": committed, "event_index": event_index}
                event_index += 1
        elif operation == "holdout_outputs":
            if committed is None:
                response = {"ok": False, "error": "prediction_commitment_required"}
            else:
                response = {"ok": True, "commitment": committed, "event_index": event_index, "rows": [{"row_id": row["row_id"], "target": row["target"], "sigma_target": row["sigma_target"]} for row in holdout]}
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
