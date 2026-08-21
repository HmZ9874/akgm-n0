"""Build a compact, immutable V41 snapshot from NASA randomized battery data."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data/nasa_v41"
OFFICIAL = DATA_ROOT / "official"
ZIP_PATH = DATA_ROOT / "Battery_Random_Walk_Room_Temp_2Post.zip"
SNAPSHOT = DATA_ROOT / "nasa_battery_dynamic_snapshot.json"
PROVENANCE = DATA_ROOT / "nasa_battery_dynamic_provenance.json"


def _sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mat_path(name: str):
    return next(OFFICIAL.rglob(f"{name}.mat"))


def _pulses(name: str):
    steps = loadmat(_mat_path(name), simplify_cells=True)["data"]["step"]
    return [
        (index, step)
        for index, step in enumerate(steps)
        if step["comment"] == "discharge (random walk)" and len(np.atleast_1d(step["time"])) >= 25
    ]


def _trace(cell: str, source_index: int, pulse, partition: str, ordinal: int):
    channels = {name: np.atleast_1d(pulse[name]) for name in ("time", "voltage", "current", "temperature")}
    count = min(len(channels[name]) for name in channels)
    sample_indices = np.unique(np.linspace(0, count - 1, 25, dtype=int))
    base_time = float(channels["time"][sample_indices[0]])
    samples = []
    for sequence_index, source_sample_index in enumerate(sample_indices):
        samples.append({
            "sequence_index": sequence_index,
            "q0": float(abs(channels["current"][source_sample_index])),
            "q1": float(channels["voltage"][source_sample_index]),
            "q2": float(channels["temperature"][source_sample_index]),
            "q3": float(channels["time"][source_sample_index] - base_time),
        })
    identity = f"{cell}:{source_index}:{ordinal}"
    return {
        "trace_id": "TRACE-" + hashlib.sha256(identity.encode()).hexdigest()[:16],
        "partition": partition,
        "source_cell": cell,
        "source_step_index": source_index,
        "samples": samples,
    }


def main():
    rw3 = _pulses("RW3")
    rw4 = _pulses("RW4")
    selections = [
        ("training", "RW3", rw3, range(0, 120, 3)),
        ("validation", "RW3", rw3, range(121, 181, 3)),
        ("future_holdout", "RW3", rw3, range(600, 660, 3)),
        ("cross_cell_replication", "RW4", rw4, range(0, 60, 3)),
    ]
    traces = []
    for partition, cell, pulses, positions in selections:
        for ordinal, position in enumerate(positions):
            source_index, pulse = pulses[position]
            traces.append(_trace(cell, source_index, pulse, partition, ordinal))
    snapshot = {
        "snapshot_version": "nasa-battery-dynamic-v41.0",
        "anonymous_channels": ["Q0", "Q1", "Q2", "Q3"],
        "human_quantity_names_exposed_to_learner": False,
        "trace_count": len(traces),
        "samples_per_trace": 25,
        "traces": traces,
    }
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    provenance = {
        "provider": "NASA Ames Prognostics Center of Excellence",
        "dataset": "Randomized Battery Usage 2: Room Temperature Random Walk",
        "landing_page": "https://data.nasa.gov/dataset/randomized-battery-usage-2-room-temperature-random-walk",
        "official_resource_url": "https://data.nasa.gov/docs/legacy/ames/2.Battery_Uniform_Distribution_Discharge_Room_Temp_DataSet_2Post.zip",
        "access_level": "public",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": _sha256(ZIP_PATH),
        "archive_bytes": ZIP_PATH.stat().st_size,
        "rw3_sha256": _sha256(_mat_path("RW3")),
        "rw4_sha256": _sha256(_mat_path("RW4")),
        "snapshot_sha256": _sha256(SNAPSHOT),
        "trace_count": len(traces),
        "partition_counts": {name: sum(trace["partition"] == name for trace in traces) for name in ("training", "validation", "future_holdout", "cross_cell_replication")},
        "official_experiment_summary": "Four 18650 Li-ion cells were repeatedly charged and discharged using randomized current sequences at room temperature, with reference cycles after fixed intervals.",
        "posthoc_channel_translation": {"Q0": "absolute measured current", "Q1": "terminal voltage", "Q2": "battery temperature", "Q3": "elapsed pulse time"},
        "learner_received_translation": False,
    }
    PROVENANCE.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(provenance, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
