from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from matio import load_from_mat

from build_calce_v52_snapshot import diagnostic_capacity, scalar_text, table_columns


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit V52 operation-level diagnostic extraction.")
    parser.add_argument("mat_file", type=Path)
    args = parser.parse_args()
    variables = load_from_mat(args.mat_file, raw_data=True)
    names = [name for name in variables if not name.startswith("__")]
    if len(names) != 1:
        raise ValueError(f"Expected one public variable, found {names}")
    records = np.asarray(variables[names[0]], dtype=object)
    print("row\toperation\tcapacity_ah\tcycle_count\tvoltage_min\tvoltage_max\tstatus")
    for row_index in range(1, records.shape[0]):
        operation = scalar_text(records[row_index, 0])
        try:
            capacity, details = diagnostic_capacity(table_columns(records[row_index, 2]))
            print(
                row_index,
                operation,
                f"{capacity:.12g}",
                int(details["cycle_count"]),
                f"{details['minimum_voltage']:.12g}",
                f"{details['maximum_voltage']:.12g}",
                "candidate",
                sep="\t",
            )
        except (KeyError, TypeError, ValueError) as error:
            print(row_index, operation, "", "", "", "", f"rejected:{error}", sep="\t")


if __name__ == "__main__":
    main()
