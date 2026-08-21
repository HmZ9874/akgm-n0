from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    AdaptiveControlExecutor,
    AdaptiveControlProgram,
    AdaptiveControlSearch,
    AdaptiveGuard,
    AdaptiveValueNode,
    InvalidAdaptiveProgram,
    NumericTableObservation,
)


ROWS = ((5, 2), (7, 3), (8, 3), (11, 4), (12, 5), (17, 5), (20, 6), (23, 7), (6, 3), (3, 5))
OUTPUTS = (1, 1, 2, 3, 2, 2, 2, 2, 0, 3)


def observation() -> NumericTableObservation:
    return NumericTableObservation.create(
        opaque_session_id="adaptive-control-test",
        input_rows=ROWS,
        output_values=OUTPUTS,
        validity_mask=(True,) * len(ROWS),
        action_receipt="anonymous-control-rows",
    )


class AdaptiveControlTests(unittest.TestCase):
    def test_search_discovers_exact_halt_and_update_without_named_target_operation(self) -> None:
        report = AdaptiveControlSearch(top_k=5).search(observation())
        winner = report.top_candidates[0]
        self.assertTrue(winner.exact)
        serialized = str(winner.program.to_dict()).lower()
        self.assertNotIn("remainder", serialized)
        self.assertNotIn("modulo", serialized)
        self.assertNotIn("multiply", serialized)
        self.assertNotIn("divide", serialized)
        self.assertEqual(winner.program.initial_state.op, "a_input")
        self.assertEqual(winner.program.guard.op, "a_less")
        self.assertEqual(winner.program.update.op, "a_subtract")

    def test_discovered_program_passes_unseen_and_boundary_rows(self) -> None:
        winner = AdaptiveControlSearch(top_k=1).search(observation()).top_candidates[0]
        executor = AdaptiveControlExecutor()
        cases = (
            ((29, 6), 5),
            ((31, 8), 7),
            ((44, 9), 8),
            ((64, 7), 1),
            ((2, 9), 2),
            ((0, 3), 0),
            ((100, 1), 0),
            ((127, 16), 15),
        )
        self.assertEqual(
            [executor.execute(winner.program, row).output_value for row, _ in cases],
            [expected for _, expected in cases],
        )

    def test_executor_rejects_update_without_state_dependency(self) -> None:
        input_0 = AdaptiveValueNode("a_input", index=0)
        input_1 = AdaptiveValueNode("a_input", index=1)
        state = AdaptiveValueNode("a_state")
        program = AdaptiveControlProgram(
            initial_state=input_0,
            guard=AdaptiveGuard("a_less", state, input_1, True),
            update=input_1,
            output=state,
        )
        with self.assertRaises(InvalidAdaptiveProgram):
            AdaptiveControlExecutor().execute(program, (5, 2))


if __name__ == "__main__":
    unittest.main()
