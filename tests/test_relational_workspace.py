from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    InvalidRelationalProgram,
    MemoryAssertion,
    MemoryInstruction,
    MicroHaltCondition,
    MicroProgram,
    MicroValueNode,
    MultiViewRelationalSearch,
    NumericObservation,
    RelationalMemoryExecutor,
    RelationalProgram,
)


def opaque_semantic() -> MicroProgram:
    zero = MicroValueNode("m_constant", constant=0)
    minus_one = MicroValueNode("m_constant", constant=-1)
    input_0 = MicroValueNode("m_input", index=0)
    input_1 = MicroValueNode("m_input", index=1)
    register_0 = MicroValueNode("m_register", index=0)
    register_1 = MicroValueNode("m_register", index=1)
    return MicroProgram(
        initial_registers=(zero, input_1),
        halt_condition=MicroHaltCondition(1, 0),
        updates=(
            MicroValueNode("m_add", (register_0, input_0)),
            MicroValueNode("m_add", (register_1, minus_one)),
        ),
        output_register=0,
    )


VALUES = (17, 42, 8, 31, 56, 23, 64, 11)


def observation() -> NumericObservation:
    return NumericObservation.create(
        opaque_session_id="multi-view-test",
        sequence_values=VALUES,
        validity_mask=(True,) * len(VALUES),
        action_receipt="multi-view",
    )


class RelationalWorkspaceTests(unittest.TestCase):
    def test_executor_supports_generated_address_reuse(self) -> None:
        program = RelationalProgram(
            input_width=8,
            instructions=(
                MemoryInstruction("r_subtract", 6, 4),
                MemoryInstruction("r_add", 8, 5),
            ),
            assertions=(MemoryAssertion(8, 2), MemoryAssertion(9, 3)),
        )
        execution = RelationalMemoryExecutor({}).execute(program, VALUES)
        self.assertEqual(execution.instruction_outputs, (8, 31))
        self.assertTrue(execution.exact)

    def test_executor_rejects_future_memory_reads(self) -> None:
        program = RelationalProgram(
            input_width=8,
            instructions=(MemoryInstruction("r_add", 8, 0),),
            assertions=(MemoryAssertion(8, 0),),
        )
        with self.assertRaises(InvalidRelationalProgram):
            RelationalMemoryExecutor({}).execute(program, VALUES)

    def test_multi_view_search_finds_local_graph_without_claiming_full_coverage(self) -> None:
        report = MultiViewRelationalSearch(
            {"SEM-test": opaque_semantic()}
        ).search(observation())
        facts = {
            (fact.instruction.op, fact.source_indices, fact.target_index)
            for fact in report.relation_facts
        }
        self.assertIn(("r_add", (2, 5), 3), facts)
        self.assertIn(("r_add", (3, 7), 1), facts)
        self.assertIn(("r_add", (2, 4), 6), facts)
        self.assertIn(("r_semantic_call", (2, 2), 6), facts)
        self.assertEqual(report.covered_indices, (1, 2, 3, 4, 5, 6, 7))
        self.assertEqual(report.uncovered_indices, (0,))
        self.assertEqual(len(report.candidates), 5)
        self.assertEqual(len({item.logic_signature for item in report.candidates}), 5)
        self.assertTrue(all(item.execution.exact for item in report.candidates))
        reuse = next(
            item for item in report.candidates if item.kind == "generated_address_reuse"
        )
        self.assertGreaterEqual(
            reuse.program.instructions[1].left_address, reuse.program.input_width
        )


if __name__ == "__main__":
    unittest.main()
