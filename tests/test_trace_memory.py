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
    InputAdapterProgram,
    NumericTableObservation,
    TraceMemoryExecutor,
    TraceMemoryProgram,
    TraceMemorySearch,
    trace_memory_program_key,
)


def verified_parent() -> InputAdapterProgram:
    input_0 = AdaptiveValueNode("a_input", index=0)
    input_1 = AdaptiveValueNode("a_input", index=1)
    state = AdaptiveValueNode("a_state")
    zero = AdaptiveValueNode("a_constant", constant=0)
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
    return InputAdapterProgram(
        parent_operation_id="BRANCH-parent",
        parent_program=branch,
        adapter_guard=AdaptiveGuard("a_less", minus_one, input_1, False),
        adapted_second_input=AdaptiveValueNode("a_subtract", (zero, input_1)),
    )


ROWS = (
    (7, 3),
    (-7, 3),
    (8, -3),
    (-8, -3),
    (11, 4),
    (-12, -5),
    (17, -5),
    (-20, -6),
    (2, 9),
    (0, -7),
)
OUTPUTS = (2, -3, 2, -3, 2, -3, 3, -4, 0, 0)


def observation() -> NumericTableObservation:
    return NumericTableObservation.create(
        opaque_session_id="trace-memory-test",
        input_rows=ROWS,
        output_values=OUTPUTS,
        validity_mask=(True,) * len(ROWS),
        action_receipt="anonymous-trace-output-rows",
    )


class TraceMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = TraceMemorySearch(
            verified_parent(), parent_operation_id="ADAPT-parent", top_k=100
        ).search(observation())
        cls.winner = cls.report.top_candidates[0]

    def test_search_discovers_exact_second_memory_updates(self) -> None:
        self.assertTrue(self.winner.exact)
        self.assertEqual(self.winner.program.initial_memory.constant, 0)
        self.assertEqual(self.winner.program.output.op, "a_state")
        serialized = str(self.winner.program.to_dict()).lower()
        self.assertNotIn("multiply", serialized)
        self.assertNotIn("divide", serialized)

    def test_second_memory_passes_unseen_signed_rows(self) -> None:
        cases = (
            ((29, -6), 4),
            ((-29, -6), -5),
            ((256, -32), 8),
            ((-256, -32), -8),
            ((-1, -1), -1),
        )
        executor = TraceMemoryExecutor()
        self.assertEqual(
            [executor.execute(self.winner.program, row).output_value for row, _ in cases],
            [expected for _, expected in cases],
        )

    def test_trace_memory_round_trip_preserves_program(self) -> None:
        restored = TraceMemoryProgram.from_dict(self.winner.program.to_dict())
        self.assertEqual(
            trace_memory_program_key(restored),
            trace_memory_program_key(self.winner.program),
        )


if __name__ == "__main__":
    unittest.main()
