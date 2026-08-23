from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from matio import load_from_mat

from build_calce_v52_snapshot import (
    ARCHIVE_SHA256,
    RAW_DIRECTORY,
    ROOT,
    Group,
    lookup,
    registered_groups,
    scalar_text,
    sha256_file,
    stable_token,
    table_columns,
    write_jsonl,
)


OUTPUT_DIRECTORY = ROOT / "data" / "calce_v521"


def cycle_capacities(columns: dict[str, np.ndarray]) -> list[dict[str, float]]:
    cycle = lookup(columns, "Cycle", "Cycle_Index")
    time = lookup(columns, "Time_sec", "Time")
    current = lookup(columns, "Current_Amp", "Current_A")
    discharge = lookup(columns, "Discharge_Ah", "Discharge_Capacity_Ah")
    voltage = lookup(columns, "Voltage_Volt", "Voltage_V")
    result: list[dict[str, float]] = []
    for cycle_id in np.unique(cycle[np.isfinite(cycle)]):
        mask = cycle == cycle_id
        finite_integration = mask & np.isfinite(time) & np.isfinite(current)
        cycle_time = time[finite_integration]
        cycle_current = current[finite_integration]
        integrated = 0.0
        if cycle_time.size >= 2:
            order = np.argsort(cycle_time, kind="stable")
            cycle_time = cycle_time[order]
            discharge_current = np.maximum(-cycle_current[order], 0.0)
            dt = np.diff(cycle_time)
            valid_dt = (dt >= 0.0) & (dt <= 120.0)
            pieces = 0.5 * (discharge_current[:-1] + discharge_current[1:]) * dt
            integrated = float(np.sum(pieces[valid_dt]) / 3600.0)
        logger_values = discharge[mask & np.isfinite(discharge)]
        logger_range = (
            float(np.max(logger_values) - np.min(logger_values)) if logger_values.size else 0.0
        )
        voltage_values = voltage[mask & np.isfinite(voltage)]
        result.append(
            {
                "cycle": float(cycle_id),
                "integrated_capacity": integrated,
                "logger_capacity": logger_range,
                "minimum_voltage": float(np.min(voltage_values)) if voltage_values.size else float("nan"),
                "maximum_voltage": float(np.max(voltage_values)) if voltage_values.size else float("nan"),
            }
        )
    return result


def latest_measurable_cycle(columns: dict[str, np.ndarray]) -> dict[str, float]:
    candidates = [item for item in cycle_capacities(columns) if item["integrated_capacity"] > 1.0e-6]
    if not candidates:
        raise ValueError("No measurable discharge cycle by current-time integration")
    return candidates[-1]


def assigned_throughput_increment(operation: str, window: float) -> float:
    number_match = re.search(r"(\d+)", operation)
    cycles = int(number_match.group(1)) if number_match else 0
    if "Partial" in operation:
        return cycles * window + 1.0
    if "Full" in operation:
        return float(cycles)
    if "Single Cycle" in operation or "Discharge" in operation:
        return 1.0
    return 0.0


def parse_cell(mat_file: Path, group: Group) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    variables = load_from_mat(mat_file, raw_data=True)
    public_names = [name for name in variables if not name.startswith("__")]
    if len(public_names) != 1:
        raise ValueError(f"Expected one public variable in {mat_file.name}, found {public_names}")
    cell_name = public_names[0]
    records = np.asarray(variables[cell_name], dtype=object)
    cell_token = stable_token("cell", cell_name)
    observations: list[dict[str, Any]] = []
    counterexamples: list[dict[str, Any]] = []
    crosschecks: list[dict[str, Any]] = []
    throughput = 0.0
    first_integrated: float | None = None
    first_logger: float | None = None

    for row_index in range(1, records.shape[0]):
        operation = scalar_text(records[row_index, 0])
        throughput += assigned_throughput_increment(operation, group.window)
        try:
            selected = latest_measurable_cycle(table_columns(records[row_index, 2]))
            integrated = selected["integrated_capacity"]
            logger = selected["logger_capacity"]
            if first_integrated is None:
                first_integrated = integrated
            if first_logger is None and logger > 1.0e-6:
                first_logger = logger
            response = integrated / first_integrated
            if not np.isfinite(response) or response <= 0:
                raise ValueError(f"Nonphysical normalized capacity {response}")
            diagnostic_index = len(observations)
            observations.append(
                {
                    "partition": "development",
                    "group_token": stable_token("group", group.group_id),
                    "cell_token": cell_token,
                    "diagnostic_index": diagnostic_index,
                    "throughput_coordinate": throughput,
                    "control_0": group.mean_level,
                    "control_1": group.window,
                    "control_2": group.rate,
                    "response": response,
                }
            )
            denominator = max(integrated, logger, 1.0e-12)
            relative_difference = abs(integrated - logger) / denominator
            crosscheck = {
                "cell_token": cell_token,
                "diagnostic_index": diagnostic_index,
                "operation_row": row_index,
                "selected_cycle": selected["cycle"],
                "integrated_capacity": integrated,
                "logger_capacity": logger,
                "relative_difference": relative_difference,
                "logger_normalized_response": logger / first_logger if first_logger else None,
            }
            crosschecks.append(crosscheck)
            if relative_difference > 0.02:
                counterexamples.append(
                    {
                        "cell": cell_name,
                        "row": row_index,
                        "operation": operation,
                        "reason": "capacity crosscheck relative difference above 0.02",
                        "details": crosscheck,
                    }
                )
        except (KeyError, TypeError, ValueError) as error:
            counterexamples.append(
                {"cell": cell_name, "row": row_index, "operation": operation, "reason": str(error)}
            )
    return observations, counterexamples, crosschecks


def parse_archive(path: Path, group: Group) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    observations: list[dict[str, Any]] = []
    counterexamples: list[dict[str, Any]] = []
    crosschecks: list[dict[str, Any]] = []
    members: list[str] = []
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix="akgm-v521-") as temp:
        for member in sorted(name for name in archive.namelist() if name.lower().endswith(".mat")):
            members.append(member)
            mat_file = Path(archive.extract(member, temp))
            cell_rows, cell_errors, cell_checks = parse_cell(mat_file, group)
            observations.extend(cell_rows)
            counterexamples.extend(cell_errors)
            crosschecks.extend(cell_checks)
    return observations, counterexamples, crosschecks, members


def build(groups: list[Group], raw_directory: Path, output_stem: str, minimum: int) -> None:
    all_rows: list[dict[str, Any]] = []
    all_counterexamples: list[dict[str, Any]] = []
    all_crosschecks: list[dict[str, Any]] = []
    archives: list[dict[str, Any]] = []
    for group in groups:
        archive_path = raw_directory / group.archive_name
        actual_hash = sha256_file(archive_path)
        expected_hash = ARCHIVE_SHA256.get(group.archive_name)
        if expected_hash is not None and actual_hash != expected_hash:
            raise ValueError(f"SHA-256 mismatch for {group.archive_name}")
        rows, errors, checks, members = parse_archive(archive_path, group)
        all_rows.extend(rows)
        all_counterexamples.extend(errors)
        all_crosschecks.extend(checks)
        archives.append(
            {
                "group_id": group.group_id,
                "archive": group.archive_name,
                "sha256": actual_hash,
                "mat_members": members,
            }
        )
        print(f"{group.group_id}: observations={len(rows)} counterexamples={len(errors)}")

    per_cell: dict[str, int] = {}
    for row in all_rows:
        per_cell[row["cell_token"]] = per_cell.get(row["cell_token"], 0) + 1
    insufficient = {cell: count for cell, count in per_cell.items() if count < minimum}
    eligible = set(per_cell) - set(insufficient)
    output_rows = [row for row in all_rows if row["cell_token"] in eligible]
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    snapshot_path = OUTPUT_DIRECTORY / f"{output_stem}_anonymous.jsonl"
    manifest_path = OUTPUT_DIRECTORY / f"{output_stem}_manifest.json"
    write_jsonl(snapshot_path, output_rows)
    manifest = {
        "schema": "v52.1-calce-current-integral-snapshot-v1",
        "observation_count": len(output_rows),
        "cell_observation_counts": per_cell,
        "ineligible_cells": insufficient,
        "archives": archives,
        "counterexamples": all_counterexamples,
        "capacity_crosschecks": all_crosschecks,
        "snapshot_sha256": sha256_file(snapshot_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"snapshot={snapshot_path.relative_to(ROOT).as_posix()}")
    print(f"manifest={manifest_path.relative_to(ROOT).as_posix()}")
    print(f"observations={len(output_rows)} cells={len(eligible)} sha256={manifest['snapshot_sha256']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build V52.1 current-integral CALCE snapshots.")
    parser.add_argument("--minimum-observations", type=int, default=8)
    args = parser.parse_args()
    groups = registered_groups({"development", "validation"})
    build(groups, RAW_DIRECTORY, "all_nonsealed", args.minimum_observations)


if __name__ == "__main__":
    main()
