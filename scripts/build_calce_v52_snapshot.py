from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from matio import load_from_mat


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION = ROOT / "experiments" / "v52_calce_preregistration.json"
RAW_DIRECTORY = ROOT / "data" / "calce_v52" / "raw" / "dev_validation"
OUTPUT_DIRECTORY = ROOT / "data" / "calce_v52"

ARCHIVE_SHA256 = {
    "SOC_0-100_2C.zip": "57ed6e023b87cff64eaa92b37176992da6fa3bdfb7a1a880ac5a55578c235348",
    "SOC_0-100_HalfC.zip": "bd0f27accfb18dd1dcc5ef1025234d81772cc58e2b178ca4b8342cbbd9370906",
    "SOC_0-60_HalfC.zip": "1cd57257bad82416cd63dd64aa57b56a1ab9e139150634bb52e13aabafac446b",
    "SOC_20-80_HalfC.zip": "5950b2fa9a037f5b272258e7b51b2848716edf342e5b67f55981e6f325b8363a",
    "SOC_40-100_HalfC.zip": "e6a55919266414ff8368fcf3e0b77070fbbdfc54274000654d92755f35539f1e",
    "SOC_40-60_2C.zip": "149d18bfed19fd1e86d1e2616df608f13824f7290807d746549ae2730010ff16",
    "SOC_40-60_HalfC.zip": "13e3d6b4ddc15e3463229bf5805a624c4140e6e03341a284e66f1bab4c0bc57c",
}


@dataclass(frozen=True)
class Group:
    group_id: str
    partition: str
    archive_name: str
    mean_level: float
    window: float
    rate: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_token(namespace: str, value: str) -> str:
    payload = f"akgm-n0-v52:{namespace}:{value}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def scalar_text(value: Any) -> str:
    array = np.asarray(value)
    if array.size == 0:
        return ""
    return str(array.reshape(-1)[0])


def table_columns(table: Any) -> dict[str, np.ndarray]:
    if isinstance(table, np.ndarray):
        if table.size != 1:
            raise ValueError(f"Expected one table object, found shape {table.shape}")
        table = table.item()
    if not hasattr(table, "properties"):
        raise TypeError(f"Expected a MATLAB table object, found {type(table).__name__}")
    properties = table.properties
    names = [scalar_text(value) for value in properties["varnames"].reshape(-1)]
    values = [np.asarray(value).reshape(-1) for value in properties["data"].reshape(-1)]
    if len(names) != len(values):
        raise ValueError("MATLAB table names and columns have different lengths")
    return dict(zip(names, values, strict=True))


def lookup(columns: dict[str, np.ndarray], *candidates: str) -> np.ndarray:
    normalized = {re.sub(r"[^a-z0-9]", "", key.lower()): key for key in columns}
    for candidate in candidates:
        key = normalized.get(re.sub(r"[^a-z0-9]", "", candidate.lower()))
        if key is not None:
            return np.asarray(columns[key], dtype=float)
    raise KeyError(f"Missing column {candidates}; available columns are {list(columns)}")


def diagnostic_capacity(columns: dict[str, np.ndarray]) -> tuple[float, dict[str, float]]:
    cycle = lookup(columns, "Cycle", "Cycle_Index")
    discharge = lookup(columns, "Discharge_Ah", "Discharge_Capacity_Ah")
    voltage = lookup(columns, "Voltage_Volt", "Voltage_V")
    finite_cycle = cycle[np.isfinite(cycle)]
    if finite_cycle.size == 0:
        raise ValueError("No finite cycle index")
    cycle_ids = np.unique(finite_cycle)
    cycle_ranges: list[float] = []
    for cycle_id in cycle_ids:
        values = discharge[(cycle == cycle_id) & np.isfinite(discharge)]
        if values.size == 0:
            cycle_ranges.append(0.0)
        else:
            cycle_ranges.append(float(np.max(values) - np.min(values)))
    maximum_range = max(cycle_ranges)
    if maximum_range <= 1.0e-6:
        raise ValueError(f"No measurable discharge cycle; maximum range {maximum_range}")
    # Some Arbin blocks end with a charge-only bookkeeping cycle. Select the
    # latest cycle whose discharge range is at least half the block maximum.
    # This also distinguishes the terminal full diagnostic from partial cycles.
    selected_index = max(
        index for index, value in enumerate(cycle_ranges) if value >= 0.5 * maximum_range
    )
    selected_cycle = cycle_ids[selected_index]
    selected_mask = cycle == selected_cycle
    selected_voltage = voltage[selected_mask & np.isfinite(voltage)]
    if selected_voltage.size == 0:
        raise ValueError("No finite voltage in selected diagnostic cycle")
    return cycle_ranges[selected_index], {
        "cycle_count": float(len(cycle_ids)),
        "selected_cycle": float(selected_cycle),
        "minimum_voltage": float(np.min(selected_voltage)),
        "maximum_voltage": float(np.max(selected_voltage)),
    }


def registered_groups(partitions: set[str]) -> list[Group]:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    groups: list[Group] = []
    for item in prereg["registered_files"]:
        if item["partition"] not in partitions:
            continue
        groups.append(
            Group(
                group_id=item["group_id"],
                partition=item["partition"],
                archive_name=Path(item["url"]).name,
                mean_level=float(item["assigned_mean_soc"]),
                window=float(item["assigned_soc_window"]),
                rate=float(item["assigned_discharge_c_rate"]),
            )
        )
    return groups


def parse_mat_file(mat_file: Path, group: Group) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    variables = load_from_mat(mat_file, raw_data=True)
    public_names = [name for name in variables if not name.startswith("__")]
    if len(public_names) != 1:
        raise ValueError(f"Expected one public variable in {mat_file.name}, found {public_names}")
    records = np.asarray(variables[public_names[0]], dtype=object)
    cell_name = public_names[0]
    cell_token = stable_token("cell", cell_name)
    observations: list[dict[str, Any]] = []
    counterexamples: list[dict[str, Any]] = []
    throughput = 0.0
    diagnostic_index = 0
    first_capacity: float | None = None

    for row_index in range(1, records.shape[0]):
        operation = scalar_text(records[row_index, 0])
        number_match = re.search(r"(\d+)", operation)
        registered_cycles = int(number_match.group(1)) if number_match else 0
        throughput += registered_cycles * group.window
        if "Single Cycle" in operation:
            throughput += 1.0

        try:
            columns = table_columns(records[row_index, 2])
            capacity, diagnostics = diagnostic_capacity(columns)
            if not np.isfinite(capacity) or capacity <= 0:
                raise ValueError(f"Nonphysical diagnostic capacity {capacity}")
            if first_capacity is None:
                first_capacity = capacity
            normalized = capacity / first_capacity
            if not np.isfinite(normalized) or normalized <= 0:
                raise ValueError(f"Nonphysical normalized capacity {normalized}")
            observations.append(
                {
                    "partition": group.partition,
                    "group_token": stable_token("group", group.group_id),
                    "cell_token": cell_token,
                    "diagnostic_index": diagnostic_index,
                    "throughput_coordinate": throughput,
                    "control_0": group.mean_level,
                    "control_1": group.window,
                    "control_2": group.rate,
                    "response": normalized,
                }
            )
            diagnostic_index += 1
            if diagnostics["maximum_voltage"] - diagnostics["minimum_voltage"] < 0.25:
                counterexamples.append(
                    {
                        "cell": cell_name,
                        "row": row_index,
                        "operation": operation,
                        "reason": "final-cycle voltage span below 0.25 V",
                        "details": diagnostics,
                    }
                )
        except (KeyError, TypeError, ValueError) as error:
            counterexamples.append(
                {
                    "cell": cell_name,
                    "row": row_index,
                    "operation": operation,
                    "reason": str(error),
                }
            )

    return observations, counterexamples


def parse_archive(path: Path, group: Group) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    observations: list[dict[str, Any]] = []
    counterexamples: list[dict[str, Any]] = []
    mat_members: list[str] = []
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix="akgm-v52-") as temp:
        for member in sorted(name for name in archive.namelist() if name.lower().endswith(".mat")):
            mat_members.append(member)
            destination = Path(archive.extract(member, temp))
            cell_observations, cell_counterexamples = parse_mat_file(destination, group)
            observations.extend(cell_observations)
            counterexamples.extend(cell_counterexamples)
    return observations, counterexamples, mat_members


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an anonymous V52 CALCE diagnostic snapshot.")
    parser.add_argument(
        "--partitions",
        nargs="+",
        choices=("development", "validation"),
        default=("development", "validation"),
    )
    parser.add_argument("--minimum-observations", type=int, default=8)
    args = parser.parse_args()
    partitions = set(args.partitions)
    groups = registered_groups(partitions)
    all_observations: list[dict[str, Any]] = []
    all_counterexamples: list[dict[str, Any]] = []
    archives: list[dict[str, Any]] = []

    for group in groups:
        archive_path = RAW_DIRECTORY / group.archive_name
        actual_hash = sha256_file(archive_path)
        expected_hash = ARCHIVE_SHA256.get(group.archive_name)
        if actual_hash != expected_hash:
            raise ValueError(
                f"SHA-256 mismatch for {group.archive_name}: expected {expected_hash}, got {actual_hash}"
            )
        observations, counterexamples, mat_members = parse_archive(archive_path, group)
        all_observations.extend(observations)
        all_counterexamples.extend(counterexamples)
        archives.append(
            {
                "group_id": group.group_id,
                "partition": group.partition,
                "archive": group.archive_name,
                "sha256": actual_hash,
                "mat_members": mat_members,
            }
        )
        print(
            f"{group.group_id}: {len(observations)} observations, "
            f"{len(counterexamples)} retained counterexamples"
        )

    per_cell: dict[str, int] = {}
    for row in all_observations:
        per_cell[row["cell_token"]] = per_cell.get(row["cell_token"], 0) + 1
    insufficient = {cell: count for cell, count in per_cell.items() if count < args.minimum_observations}
    eligible_cells = set(per_cell) - set(insufficient)
    eligible_observations = [
        row for row in all_observations if row["cell_token"] in eligible_cells
    ]

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    stem = "_".join(sorted(partitions))
    snapshot_path = OUTPUT_DIRECTORY / f"v52_{stem}_anonymous.jsonl"
    manifest_path = OUTPUT_DIRECTORY / f"v52_{stem}_manifest.json"
    write_jsonl(snapshot_path, eligible_observations)
    manifest = {
        "schema": "v52-calce-anonymous-snapshot-v1",
        "partitions": sorted(partitions),
        "candidate_observation_count": len(all_observations),
        "observation_count": len(eligible_observations),
        "cell_observation_counts": per_cell,
        "ineligible_cells_below_registered_minimum": insufficient,
        "archives": archives,
        "counterexamples": all_counterexamples,
        "snapshot_sha256": sha256_file(snapshot_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"snapshot={snapshot_path.relative_to(ROOT).as_posix()}")
    print(f"manifest={manifest_path.relative_to(ROOT).as_posix()}")
    print(
        f"observations={len(eligible_observations)} candidate_observations={len(all_observations)} "
        f"eligible_cells={len(eligible_cells)} ineligible_cells={len(insufficient)}"
    )
    print(f"snapshot_sha256={manifest['snapshot_sha256']}")


if __name__ == "__main__":
    main()
