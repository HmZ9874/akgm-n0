from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    IndexedExecutor,
    IndexedSemanticSearch,
    MicroHaltCondition,
    MicroProgram,
    MicroValueNode,
    NumericObservation,
    build_difference_workspace,
    micro_program_key,
)


def anonymous_binary_semantic() -> MicroProgram:
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


def observation() -> NumericObservation:
    return NumericObservation.create(
        opaque_session_id="indexed-test",
        sequence_values=(2, 6, 12, 20, 30, 42, 56),
        validity_mask=(True,) * 7,
        action_receipt="ordered-values",
    )


class IndexedSemanticTests(unittest.TestCase):
    def test_micro_program_round_trip_is_safe_and_exact(self) -> None:
        source = anonymous_binary_semantic()
        restored = MicroProgram.from_dict(source.to_dict())
        self.assertEqual(micro_program_key(source), micro_program_key(restored))
        with self.assertRaises(ValueError):
            MicroProgram.from_dict({**source.to_dict(), "unexpected": "field"})

    def test_difference_workspace_is_generic_adjacent_subtraction(self) -> None:
        workspace = build_difference_workspace(observation())
        self.assertEqual(workspace.first_layer, (4, 6, 8, 10, 12, 14))
        self.assertEqual(workspace.second_layer, (2, 2, 2, 2, 2))
        self.assertIn(1.0, {item["value"] for item in workspace.evidence_constants})
        self.assertIn(2.0, {item["value"] for item in workspace.evidence_constants})

    def test_opaque_semantic_enables_exact_relation_without_intrinsic_product_node(self) -> None:
        operation_id = "SEM-test-opaque"
        without_library = IndexedSemanticSearch({}, top_k=5).search(observation())
        with_library = IndexedSemanticSearch(
            {operation_id: anonymous_binary_semantic()}, top_k=5
        ).search(observation())

        self.assertFalse(any(item.exact for item in without_library.top_candidates))
        winner = with_library.top_candidates[0]
        self.assertTrue(winner.exact)
        serialized = winner.program.to_dict()
        self.assertIn(operation_id, str(serialized))
        self.assertNotIn("multiply", str(serialized).lower())
        self.assertNotIn("divide", str(serialized).lower())
        executor = IndexedExecutor({operation_id: anonymous_binary_semantic()})
        self.assertEqual(
            [executor.execute(winner.program, index) for index in range(7, 12)],
            [72, 90, 110, 132, 156],
        )


if __name__ == "__main__":
    unittest.main()
