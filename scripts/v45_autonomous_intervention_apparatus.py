"""Sealed JSON-lines computational intervention apparatus for V45."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time


RANGES = ((2, 8), (2, 8), (1, 4))
ALL_ACTIONS = tuple(
    (q0, q1, q2)
    for q0 in range(RANGES[0][0], RANGES[0][1] + 1)
    for q1 in range(RANGES[1][0], RANGES[1][1] + 1)
    for q2 in range(RANGES[2][0], RANGES[2][1] + 1)
)


def _partition(action):
    digest = hashlib.sha256(json.dumps(action, separators=(",", ":")).encode()).digest()
    return "transfer" if digest[0] % 7 == 0 else "development"


DEVELOPMENT_ACTIONS = tuple(action for action in ALL_ACTIONS if _partition(action) == "development")
TRANSFER_ACTIONS = tuple(action for action in ALL_ACTIONS if _partition(action) == "transfer")


def _experiment(action):
    q0, q1, q2 = action
    operations = 0
    checksum = 0
    started = time.perf_counter_ns()
    for left in range(q0):
        for right in range(q1):
            for depth in range(q2):
                operations += 1
                checksum = (checksum + ((left + 3 * right + 5 * depth) & 15)) & 0xFFFFFFFF
    if q0 > q1:
        for left in range(q0):
            operations += 1
            checksum ^= (left * 17) & 0xFFFFFFFF
    elapsed = time.perf_counter_ns() - started
    return {
        "values": list(action),
        "response": float(operations),
        "elapsed_ns": elapsed,
        "checksum": checksum,
        "measurement_id": "MEAS-" + hashlib.sha256(
            json.dumps([action, operations, checksum], separators=(",", ":")).encode()
        ).hexdigest()[:16],
    }


def _batch_commitment(batch_id, order, randomization_commitment):
    payload = {
        "batch_id": batch_id,
        "order": order,
        "randomization_commitment": randomization_commitment,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main():
    event_index = 0
    pending = None
    measured = set()
    program_commitment = None
    for line in sys.stdin:
        request = json.loads(line)
        operation = request.get("op")
        if operation == "metadata":
            response = {
                "ok": True,
                "broker_pid": os.getpid(),
                "control_count": len(RANGES),
                "safe_ranges": [list(item) for item in RANGES],
                "development_actions": [list(item) for item in DEVELOPMENT_ACTIONS],
                "sealed_transfer_action_count": len(TRANSFER_ACTIONS),
                "maximum_development_experiments": 20,
                "mechanism_exposed": False,
                "control_names_exposed": False,
                "response_exists_before_action": False,
            }
        elif operation == "commit_batch":
            order = [tuple(map(int, item)) for item in request.get("order", ())]
            serialized = [list(item) for item in order]
            expected = _batch_commitment(
                str(request.get("batch_id")), serialized,
                str(request.get("randomization_commitment")),
            )
            valid = (
                pending is None
                and expected == request.get("commitment")
                and 0 < len(order) <= 10
                and len(order) == len(set(order))
                and all(item in DEVELOPMENT_ACTIONS and item not in measured for item in order)
                and len(measured) + len(order) <= 20
            )
            if not valid:
                response = {"ok": False, "error": "invalid_or_unsafe_batch_commitment"}
            else:
                pending = {"batch_id": str(request["batch_id"]), "order": order, "commitment": expected}
                response = {"ok": True, "event_index": event_index, "commitment": expected}
                event_index += 1
        elif operation == "run_batch":
            if pending is None:
                response = {"ok": False, "error": "batch_commitment_required"}
            else:
                started = time.time_ns()
                results = [_experiment(action) for action in pending["order"]]
                ended = time.time_ns()
                measured.update(pending["order"])
                response = {
                    "ok": True,
                    "event_index": event_index,
                    "batch_id": pending["batch_id"],
                    "batch_commitment": pending["commitment"],
                    "results": results,
                    "started_at_unix_ns": started,
                    "ended_at_unix_ns": ended,
                }
                pending = None
                event_index += 1
        elif operation == "commit_program":
            digest = str(request.get("commitment", ""))
            if program_commitment is not None or len(digest) != 64:
                response = {"ok": False, "error": "invalid_or_duplicate_program_commitment"}
            else:
                program_commitment = digest
                response = {"ok": True, "event_index": event_index, "commitment": digest}
                event_index += 1
        elif operation == "run_transfer":
            if program_commitment is None or request.get("commitment") != program_commitment:
                response = {"ok": False, "error": "program_commitment_required"}
            else:
                response = {
                    "ok": True,
                    "event_index": event_index,
                    "commitment": program_commitment,
                    "results": [_experiment(action) for action in TRANSFER_ACTIONS],
                    "mechanism_exposed_to_program": False,
                }
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
