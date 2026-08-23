from __future__ import annotations

import numpy as np

from scripts.build_calce_v52_snapshot import diagnostic_capacity


def test_diagnostic_capacity_handles_cumulative_counter() -> None:
    columns = {
        "Cycle": np.asarray([1, 1, 2, 2, 3, 3], dtype=float),
        "Discharge_Ah": np.asarray([0.0, 0.2, 0.2, 0.4, 0.4, 1.8]),
        "Voltage_Volt": np.asarray([4.0, 3.7, 4.0, 3.7, 4.2, 2.75]),
    }
    capacity, details = diagnostic_capacity(columns)
    assert np.isclose(capacity, 1.4)
    assert details["selected_cycle"] == 3.0


def test_diagnostic_capacity_skips_terminal_charge_only_cycle() -> None:
    columns = {
        "Cycle": np.asarray([1, 1, 2, 2, 3, 3], dtype=float),
        "Discharge_Ah": np.asarray([0.0, 1.4, 0.0, 1.3, 0.0, 0.0]),
        "Voltage_Volt": np.asarray([4.2, 2.75, 4.2, 2.8, 3.3, 4.2]),
    }
    capacity, details = diagnostic_capacity(columns)
    assert np.isclose(capacity, 1.3)
    assert details["selected_cycle"] == 2.0
