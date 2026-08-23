from __future__ import annotations

import argparse
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from matio import load_from_mat

from build_calce_v52_snapshot import RAW_DIRECTORY, ROOT, Group, registered_groups, scalar_text, stable_token, table_columns
from build_calce_v521_snapshot import (
    assigned_throughput_increment,
    build,
    cycle_capacities,
)


OUTPUT_DIRECTORY = ROOT / "data" / "calce_v522"
MINIMUM_RELATIVE_CAPACITY = 0.10


def parse_cell_relative(
    mat_file: Path, group: Group
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
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
    initial_capacity: float | None = None
    initial_logger: float | None = None

    for row_index in range(1, records.shape[0]):
        operation = scalar_text(records[row_index, 0])
        throughput += assigned_throughput_increment(operation, group.window)
        try:
            cycles = cycle_capacities(table_columns(records[row_index, 2]))
            threshold = 1.0e-6 if initial_capacity is None else MINIMUM_RELATIVE_CAPACITY * initial_capacity
            eligible = [item for item in cycles if item["integrated_capacity"] >= threshold]
            if not eligible:
                raise ValueError(f"No discharge cycle above registered threshold {threshold}")
            selected = eligible[-1]
            integrated = selected["integrated_capacity"]
            logger = selected["logger_capacity"]
            if initial_capacity is None:
                initial_capacity = integrated
            if initial_logger is None and logger > 1.0e-6:
                initial_logger = logger
            response = integrated / initial_capacity
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
                "logger_normalized_response": logger / initial_logger if initial_logger else None,
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


def parse_archive_relative(
    path: Path, group: Group
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    observations: list[dict[str, Any]] = []
    counterexamples: list[dict[str, Any]] = []
    crosschecks: list[dict[str, Any]] = []
    members: list[str] = []
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix="akgm-v522-") as temp:
        for member in sorted(name for name in archive.namelist() if name.lower().endswith(".mat")):
            members.append(member)
            mat_file = Path(archive.extract(member, temp))
            rows, errors, checks = parse_cell_relative(mat_file, group)
            observations.extend(rows)
            counterexamples.extend(errors)
            crosschecks.extend(checks)
    return observations, counterexamples, crosschecks, members


def main() -> None:
    parser = argparse.ArgumentParser(description="Build V52.2 CALCE snapshots.")
    parser.add_argument("--sealed", action="store_true")
    args = parser.parse_args()
    if args.sealed:
        groups = registered_groups({"sealed"})
        raw_directory = ROOT / "data" / "calce_v522" / "raw" / "sealed"
        output_stem = "sealed"
    else:
        groups = registered_groups({"development", "validation"})
        raw_directory = RAW_DIRECTORY
        output_stem = "all_nonsealed"
    build(
        groups,
        raw_directory,
        output_stem,
        8,
        archive_parser=parse_archive_relative,
        output_directory=OUTPUT_DIRECTORY,
        schema="v52.2-calce-relative-diagnostic-snapshot-v1",
    )


if __name__ == "__main__":
    main()
