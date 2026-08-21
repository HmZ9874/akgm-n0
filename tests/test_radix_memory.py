from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    AdaptiveBranchProgram,
    AdaptiveControlProgram,
    AdaptiveGuard,
    AdaptiveValueNode,
    InputAdapterProgram,
    NumericTableObservation,
    RadixMemoryExecutor,
    RadixMemoryProgram,
    RadixMemorySearch,
    TraceMemoryProgram,
    radix_memory_program_key,
)


def trace_parent() -> TraceMemoryProgram:
    input_0 = AdaptiveValueNode("a_input", index=0)
    input_1 = AdaptiveValueNode("a_input", index=1)
    state = AdaptiveValueNode("a_state")
    zero = AdaptiveValueNode("a_constant", constant=0)
    one = AdaptiveValueNode("a_constant", constant=1)
    minus_one = AdaptiveValueNode("a_constant", constant=-1)
    base = AdaptiveControlProgram(
        initial_state=input_0,
        guard=AdaptiveGuard("a_less", state, input_1, True),
        update=AdaptiveValueNode("a_subtract", (state, input_1)),
        output=state,
    )
    branch = AdaptiveBranchProgram(
        parent_operation_id="CTRL-parent",
        base_program=base,
        branch_guard=AdaptiveGuard("a_less", minus_one, state, False),
        branch_update=AdaptiveValueNode("a_add", (state, input_1)),
    )
    adapter = InputAdapterProgram(
        parent_operation_id="BRANCH-parent",
        parent_program=branch,
        adapter_guard=AdaptiveGuard("a_less", minus_one, input_1, False),
        adapted_second_input=AdaptiveValueNode("a_subtract", (zero, input_1)),
    )
    return TraceMemoryProgram(
        parent_operation_id="ADAPT-parent",
        parent_program=adapter,
        initial_memory=zero,
        priority_memory_update=AdaptiveValueNode("a_subtract", (state, one)),
        base_memory_update=AdaptiveValueNode("a_add", (state, one)),
        output=state,
    )


ROWS = (
    (1, 10),
    (1, 100),
    (1, 1000),
    (1, 2),
    (3, 4),
    (1, 8),
    (7, 20),
    (9, 25),
    (13, 40),
    (-1, 8),
    (-7, 20),
    (23, -10),
)
OUTPUTS = (0.1, 0.01, 0.001, 0.5, 0.75, 0.125, 0.35, 0.36, 0.325, -0.125, -0.35, 2.3)


def observation() -> NumericTableObservation:
    return NumericTableObservation.create(
        opaque_session_id="multistage-residual-test",
        input_rows=ROWS,
        output_values=OUTPUTS,
        validity_mask=(True,) * len(ROWS),
        action_receipt="anonymous-noninteger-output-rows",
    )


class RadixMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = RadixMemorySearch(
            trace_parent(), parent_operation_id="TRACE-parent", top_k=50
        ).search(observation())
        cls.winner = cls.report.top_candidates[0]

    def test_search_discovers_coherent_multistage_weights(self) -> None:
        self.assertTrue(self.winner.exact)
        self.assertEqual(self.winner.program.cycle_width, 10)
        self.assertEqual(self.winner.program.stage_weights, ("0.1", "0.01", "0.001"))
        self.assertEqual(self.winner.coherence_error, 0)
        serialized = str(self.winner.program.to_dict()).lower()
        for forbidden in ("multiply", "divide", "quotient", "decimal"):
            self.assertNotIn(forbidden, serialized)

    def test_multistage_program_passes_unseen_hundredths_and_thousandths(self) -> None:
        executor = RadixMemoryExecutor()
        cases = (
            ((17, 8), Decimal("2.125")),
            ((-17, -8), Decimal("-2.125")),
            ((37, 40), Decimal("0.925")),
            ((1, 125), Decimal("0.008")),
            ((999, 1000), Decimal("0.999")),
            ((-1001, -1000), Decimal("-1.001")),
        )
        self.assertEqual(
            [executor.execute(self.winner.program, row).output_decimal for row, _ in cases],
            [expected for _, expected in cases],
        )

    def test_multistage_program_round_trip_is_exact(self) -> None:
        restored = RadixMemoryProgram.from_dict(self.winner.program.to_dict())
        self.assertEqual(
            radix_memory_program_key(restored),
            radix_memory_program_key(self.winner.program),
        )


if __name__ == "__main__":
    unittest.main()
