from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    AdaptiveBranchProgram,
    AdaptiveControlProgram,
    AdaptiveGuard,
    AdaptiveValueNode,
    InputAdapterExecutor,
    InputAdapterSearch,
    InvalidAdaptiveProgram,
    NumericTableObservation,
)


def parent_program() -> AdaptiveBranchProgram:
    input_0 = AdaptiveValueNode("a_input", index=0)
    input_1 = AdaptiveValueNode("a_input", index=1)
    state = AdaptiveValueNode("a_state")
    minus_one = AdaptiveValueNode("a_constant", constant=-1)
    base = AdaptiveControlProgram(
        initial_state=input_0,
        guard=AdaptiveGuard("a_less", state, input_1, True),
        update=AdaptiveValueNode("a_subtract", (state, input_1)),
        output=state,
    )
    return AdaptiveBranchProgram(
        parent_operation_id="CTRL-parent",
        base_program=base,
        branch_guard=AdaptiveGuard("a_less", minus_one, state, False),
        branch_update=AdaptiveValueNode("a_add", (state, input_1)),
    )


ROWS = ((7, -3), (-7, -3), (8, -3), (-8, -3), (11, -4), (-12, -5), (7, 3), (-7, 3))
OUTPUTS = (1, 2, 2, 1, 3, 3, 1, 2)


def observation() -> NumericTableObservation:
    return NumericTableObservation.create(
        opaque_session_id="input-adapter-test",
        input_rows=ROWS,
        output_values=OUTPUTS,
        validity_mask=(True,) * len(ROWS),
        action_receipt="mixed-sign-second-inputs",
    )


class InputAdapterTests(unittest.TestCase):
    def test_search_discovers_exact_conditional_second_input_adapter(self) -> None:
        report = InputAdapterSearch(
            parent_program(), parent_operation_id="BRANCH-parent", top_k=5
        ).search(observation())
        winner = report.top_candidates[0]
        self.assertTrue(winner.exact)
        self.assertEqual(winner.program.adapted_second_input.op, "a_subtract")
        self.assertEqual(
            winner.adapted_second_inputs,
            (3, 3, 3, 3, 4, 5, 3, 3),
        )
        self.assertGreaterEqual(len(report.failed_candidates), 1)

    def test_adapter_passes_unseen_sign_combinations(self) -> None:
        winner = InputAdapterSearch(
            parent_program(), parent_operation_id="BRANCH-parent", top_k=1
        ).search(observation()).top_candidates[0]
        executor = InputAdapterExecutor()
        cases = (
            ((29, -6), 5),
            ((-29, -6), 1),
            ((31, -8), 7),
            ((-31, -8), 1),
            ((-29, 6), 1),
        )
        self.assertEqual(
            [executor.execute(winner.program, row).output_value for row, _ in cases],
            [expected for _, expected in cases],
        )

    def test_zero_second_input_remains_outside_scope(self) -> None:
        winner = InputAdapterSearch(
            parent_program(), parent_operation_id="BRANCH-parent", top_k=1
        ).search(observation()).top_candidates[0]
        with self.assertRaises(InvalidAdaptiveProgram):
            InputAdapterExecutor().execute(winner.program, (7, 0))


if __name__ == "__main__":
    unittest.main()
