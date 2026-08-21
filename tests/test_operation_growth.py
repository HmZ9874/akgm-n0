from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenIntegerGridEnvironment
from akgm_n0.learner import (
    InvalidIterationProgram,
    IterationExecutor,
    IterationProgram,
    IterationProgramSearch,
    NumericTableObservation,
    ValueNode,
)


SECRET = b"operation-growth-tests"


class OperationGrowthTests(unittest.TestCase):
    def make_development_observation(self) -> NumericTableObservation:
        rows = (
            (0, 0),
            (0, 3),
            (1, 0),
            (1, 1),
            (2, 3),
            (3, 2),
            (4, 1),
            (-2, 3),
            (5, 4),
        )
        return HiddenIntegerGridEnvironment(rows, seed=101, secret=SECRET).observe()

    def test_public_table_surface_is_exact(self) -> None:
        observation = self.make_development_observation()
        self.assertEqual(
            set(observation.to_public_dict()),
            {
                "opaque_session_id",
                "input_rows",
                "output_values",
                "validity_mask",
                "action_receipt",
            },
        )

    def test_runtime_rejects_unregistered_operations(self) -> None:
        unsupported = ValueNode(
            "p_multiply",
            args=(ValueNode("p_input", column_index=0), ValueNode("p_input", column_index=1)),
        )
        program = IterationProgram(
            1,
            ValueNode("p_subtract", args=(ValueNode("p_input", column_index=0), ValueNode("p_input", column_index=0))),
            unsupported,
        )
        with self.assertRaises(InvalidIterationProgram):
            IterationExecutor().evaluate(program, (2, 3))

    def test_search_is_deterministic_and_finds_exact_program(self) -> None:
        search = IterationProgramSearch(top_k=20)
        first = search.search(self.make_development_observation())
        second = search.search(self.make_development_observation())
        self.assertEqual(
            [item.candidate_id for item in first.top_candidates],
            [item.candidate_id for item in second.top_candidates],
        )
        exact = [item for item in first.top_candidates if item.fit_error == 0.0]
        self.assertTrue(exact)
        self.assertEqual(exact[0].program.to_dict()["op"], "p_iterate")

    def test_exact_candidate_passes_unseen_rows(self) -> None:
        report = IterationProgramSearch(top_k=20).search(
            self.make_development_observation()
        )
        candidate = next(item for item in report.top_candidates if item.fit_error == 0.0)
        executor = IterationExecutor()
        hidden_rows = ((7, 5), (-4, 6), (11, 0), (2, 9), (9, 2))
        hidden = HiddenIntegerGridEnvironment(
            hidden_rows, seed=202, secret=SECRET
        ).observe()
        predictions = tuple(
            executor.evaluate(candidate.program, row) for row in hidden.input_rows
        )
        self.assertEqual(predictions, hidden.output_values)

    def test_control_bounds_are_enforced(self) -> None:
        zero = ValueNode(
            "p_subtract",
            args=(ValueNode("p_input", column_index=0), ValueNode("p_input", column_index=0)),
        )
        update = ValueNode(
            "p_add",
            args=(ValueNode("p_accumulator"), ValueNode("p_input", column_index=0)),
        )
        program = IterationProgram(1, zero, update)
        executor = IterationExecutor(maximum_control_steps=4)
        with self.assertRaises(InvalidIterationProgram):
            executor.evaluate(program, (2, 5))
        with self.assertRaises(InvalidIterationProgram):
            executor.evaluate(program, (2, -1))
        with self.assertRaises(InvalidIterationProgram):
            executor.evaluate(program, (2, 1.5))


if __name__ == "__main__":
    unittest.main()
