"""JSON-lines live timing apparatus for V39 randomized interventions."""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
import time

LEVELS = (48, 64, 80, 96, 112, 128, 160, 192, 224, 256, 288, 320, 352)


def _kernel(level: int, cycles: int):
    accumulator = 0
    for cycle in range(cycles):
        for left in range(level):
            for right in range(level):
                accumulator = (accumulator + ((left ^ right ^ cycle) & 7)) & 0xFFFFFFFF
    return accumulator


def _measure(level: int):
    cycles = max(4, 1_200_000 // (level * level))
    samples = []
    checksum = 0
    for _ in range(5):
        started = time.perf_counter_ns()
        checksum ^= _kernel(level, cycles)
        elapsed = time.perf_counter_ns() - started
        samples.append(elapsed / cycles)
    median = statistics.median(samples)
    mad = statistics.median(abs(value - median) for value in samples)
    return {"level": level, "response_ns_per_cycle": median, "mad_ns_per_cycle": mad, "samples": samples, "cycles": cycles, "checksum": checksum}


def _commitment(batch_id, order, seed_commitment):
    payload = {"batch_id": batch_id, "order": order, "seed_commitment": seed_commitment}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    measured = set()
    pending = None
    prediction_commitments = []
    event_index = 0
    _kernel(16, 2)
    for line in sys.stdin:
        request = json.loads(line)
        operation = request.get("op")
        if operation == "metadata":
            response = {"ok": True, "broker_pid": os.getpid(), "apparatus": "live_nested_workload_timer_v39", "available_levels": list(LEVELS), "clock": "perf_counter_ns", "measurement_exists_before_request": False}
        elif operation == "commit_prediction":
            digest = str(request.get("commitment", ""))
            if len(digest) != 64:
                response = {"ok": False, "error": "invalid_prediction_commitment"}
            else:
                response = {"ok": True, "event_index": event_index, "commitment": digest, "committed_at_unix_ns": time.time_ns()}
                prediction_commitments.append(response)
                event_index += 1
        elif operation == "commit_batch":
            order = [int(value) for value in request["order"]]
            expected = _commitment(request["batch_id"], order, request["seed_commitment"])
            valid = expected == request["commitment"] and len(order) == len(set(order)) and all(value in LEVELS and value not in measured for value in order)
            requires_prediction = bool(request.get("requires_prediction", False))
            if pending is not None or not valid or (requires_prediction and not prediction_commitments):
                response = {"ok": False, "error": "invalid_or_overlapping_batch_commitment"}
            else:
                pending = dict(request)
                response = {"ok": True, "event_index": event_index, "commitment": expected}
                event_index += 1
        elif operation == "run_batch":
            if pending is None:
                response = {"ok": False, "error": "batch_commitment_required"}
            else:
                started_at = time.time_ns()
                results = [_measure(int(level)) for level in pending["order"]]
                ended_at = time.time_ns()
                measured.update(int(level) for level in pending["order"])
                response = {"ok": True, "event_index": event_index, "batch_id": pending["batch_id"], "commitment": pending["commitment"], "started_at_unix_ns": started_at, "ended_at_unix_ns": ended_at, "results": results}
                event_index += 1
                pending = None
        elif operation == "shutdown":
            print(json.dumps({"ok": True}), flush=True)
            return 0
        else:
            response = {"ok": False, "error": "unsupported_operation"}
        print(json.dumps(response, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
