from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from matio import load_from_mat

from build_calce_v52_snapshot import lookup, scalar_text, table_columns


def integrate_discharge_by_cycle(columns: dict[str, np.ndarray]) -> list[tuple[float, float]]:
    cycle = lookup(columns, "Cycle", "Cycle_Index")
    time = lookup(columns, "Time_sec", "Time")
    current = lookup(columns, "Current_Amp", "Current_A")
    result: list[tuple[float, float]] = []
    for cycle_id in np.unique(cycle[np.isfinite(cycle)]):
        mask = (cycle == cycle_id) & np.isfinite(time) & np.isfinite(current)
        cycle_time = time[mask]
        cycle_current = current[mask]
        if cycle_time.size < 2:
            result.append((float(cycle_id), 0.0))
            continue
        order = np.argsort(cycle_time, kind="stable")
        cycle_time = cycle_time[order]
        discharge_current = np.maximum(-cycle_current[order], 0.0)
        dt = np.diff(cycle_time)
        valid = (dt >= 0.0) & (dt <= 120.0)
        trapezoids = 0.5 * (discharge_current[:-1] + discharge_current[1:]) * dt
        result.append((float(cycle_id), float(np.sum(trapezoids[valid]) / 3600.0)))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit CALCE capacity using current-time integration.")
    parser.add_argument("mat_file", type=Path)
    args = parser.parse_args()
    variables = load_from_mat(args.mat_file, raw_data=True)
    names = [name for name in variables if not name.startswith("__")]
    records = np.asarray(variables[names[0]], dtype=object)
    print("row\toperation\tselected_cycle\tintegrated_discharge_ah\tblock_max_ah")
    for row_index in range(1, records.shape[0]):
        operation = scalar_text(records[row_index, 0])
        try:
            capacities = integrate_discharge_by_cycle(table_columns(records[row_index, 2]))
            maximum = max(value for _, value in capacities)
            if maximum <= 1.0e-6:
                raise ValueError("no measurable discharge")
            eligible = [(cycle, value) for cycle, value in capacities if value >= 0.5 * maximum]
            cycle, capacity = eligible[-1]
            print(row_index, operation, cycle, f"{capacity:.12g}", f"{maximum:.12g}", sep="\t")
        except (KeyError, TypeError, ValueError) as error:
            print(row_index, operation, "", "", f"rejected:{error}", sep="\t")


if __name__ == "__main__":
    main()
