"""Create a post-commit blind challenge from previously unused NASA cells RW5/RW6."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nasa_v41"
OFFICIAL = DATA / "official"
REPORT = ROOT / "reports/data/official_dynamic_science_v41_latest.json"
SNAPSHOT = DATA / "nasa_battery_v41_blind_challenge.json"
PROVENANCE = DATA / "nasa_battery_v41_blind_challenge_provenance.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pulses(cell):
    path = next(OFFICIAL.rglob(f"{cell}.mat"))
    steps = loadmat(path, simplify_cells=True)["data"]["step"]
    pulses = [
        (index, step) for index, step in enumerate(steps)
        if step["comment"] == "discharge (random walk)" and len(np.atleast_1d(step["time"])) >= 25
    ]
    return path, pulses


def _trace(cell, stage, source_index, pulse, ordinal):
    channels = {name: np.atleast_1d(pulse[name]) for name in ("time", "voltage", "current", "temperature")}
    count = min(len(value) for value in channels.values())
    indices = np.unique(np.linspace(0, count - 1, 25, dtype=int))
    base_time = float(channels["time"][indices[0]])
    samples = [
        {
            "sequence_index": sequence,
            "q0": float(abs(channels["current"][index])),
            "q1": float(channels["voltage"][index]),
            "q2": float(channels["temperature"][index]),
            "q3": float(channels["time"][index] - base_time),
        }
        for sequence, index in enumerate(indices)
    ]
    identity = f"challenge:{cell}:{stage}:{source_index}:{ordinal}"
    return {
        "trace_id": "CHALLENGE-" + hashlib.sha256(identity.encode()).hexdigest()[:16],
        "source_cell": cell,
        "life_stage": stage,
        "source_step_index": source_index,
        "samples": samples,
    }


def main():
    frozen = json.loads(REPORT.read_text(encoding="utf-8"))
    selected = frozen["acceptance"]["discovery"]["selected"]
    traces = []
    source_files = {}
    for cell in ("RW5", "RW6"):
        path, pulses = _pulses(cell)
        source_files[cell] = {"sha256": _sha256(path), "bytes": path.stat().st_size}
        stage_positions = {
            "early": list(range(0, 60, 3)),
            "middle": list(range(len(pulses) // 2 - 30, len(pulses) // 2 + 30, 3)),
            "late": list(range(len(pulses) - 60, len(pulses), 3)),
        }
        for stage, positions in stage_positions.items():
            for ordinal, position in enumerate(positions):
                source_index, pulse = pulses[position]
                traces.append(_trace(cell, stage, source_index, pulse, ordinal))
    snapshot = {
        "challenge_version": "nasa-battery-v41-blind-challenge.0",
        "frozen_program_id": selected["program_id"],
        "frozen_program_opaque": selected["opaque_program"],
        "frozen_report_created_at": frozen["created_at"],
        "challenge_created_at": datetime.now(timezone.utc).isoformat(),
        "program_refit_allowed": False,
        "human_quantity_names_exposed_to_program": False,
        "trace_count": len(traces),
        "traces": traces,
    }
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    provenance = {
        "provider": "NASA Ames Prognostics Center of Excellence",
        "parent_archive_sha256": frozen["acceptance"]["dataset"]["provenance_audit"]["archive_sha256"],
        "source_files": source_files,
        "snapshot_sha256": _sha256(SNAPSHOT),
        "trace_count": len(traces),
        "cell_counts": {cell: sum(trace["source_cell"] == cell for trace in traces) for cell in ("RW5", "RW6")},
        "stage_counts": {stage: sum(trace["life_stage"] == stage for trace in traces) for stage in ("early", "middle", "late")},
        "frozen_program_precedes_challenge": frozen["created_at"] < snapshot["challenge_created_at"],
        "program_id": selected["program_id"],
        "program_refit_allowed": False,
    }
    PROVENANCE.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(provenance, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
