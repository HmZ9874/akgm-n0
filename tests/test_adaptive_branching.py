from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    AdaptiveBranchExecutor,
    AdaptiveBranchSearch,
    AdaptiveControlProgram,
    AdaptiveControlSearch,
    NumericTableObservation,
    adaptive_program_key,
)


POSITIVE_ROWS = ((5, 2), (7, 3), (8, 3), (11, 4), (12, 5), (6, 3), (3, 5))
POSITIVE_OUTPUTS = (1, 1, 2, 3, 2, 0, 3)
SIGNED_ROWS = ((-7, 3), (-8, 3), (-11, 4), (-12, 5), (-17, 5), (-20, 6), (-3, 5), (7, 3), (0, 3))
SIGNED_OUTPUTS = (2, 1, 1, 3, 3, 4, 2, 1, 0)


def table(rows, outputs) -> NumericTableObservation:
    return NumericTableObservation.create(
        opaque_session_id="adaptive-branch-test",
        input_rows=rows,
        output_values=outputs,
        validity_mask=(True,) * len(rows),
        action_receipt="anonymous-signed-rows",
    )


class AdaptiveBranchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = AdaptiveControlSearch(top_k=1).search(
            table(POSITIVE_ROWS, POSITIVE_OUTPUTS)
        ).top_candidates[0].program

    def test_parent_program_round_trip_preserves_operation_identity(self) -> None:
        restored = AdaptiveControlProgram.from_dict(self.base.to_dict())
        self.assertEqual(adaptive_program_key(restored), adaptive_program_key(self.base))

    def test_search_grows_exact_priority_branch_for_signed_rows(self) -> None:
        report = AdaptiveBranchSearch(
            self.base, parent_operation_id="CTRL-parent", top_k=5
        ).search(table(SIGNED_ROWS, SIGNED_OUTPUTS))
        winner = report.top_candidates[0]
        self.assertTrue(winner.exact)
        self.assertEqual(winner.program.branch_update.op, "a_add")
        self.assertIn("a_less", str(winner.program.branch_guard.to_dict()))
        self.assertEqual(winner.program.base_program, self.base)

    def test_signed_branch_passes_unseen_negative_rows_and_preserves_positive_parent(self) -> None:
        winner = AdaptiveBranchSearch(
            self.base, parent_operation_id="CTRL-parent", top_k=1
        ).search(table(SIGNED_ROWS, SIGNED_OUTPUTS)).top_candidates[0]
        executor = AdaptiveBranchExecutor()
        cases = (
            ((-29, 6), 1),
            ((-31, 8), 1),
            ((-44, 9), 1),
            ((-64, 7), 6),
            ((-2, 9), 7),
            ((29, 6), 5),
            ((0, 7), 0),
        )
        self.assertEqual(
            [executor.execute(winner.program, row).output_value for row, _ in cases],
            [expected for _, expected in cases],
        )


if __name__ == "__main__":
    unittest.main()
