from __future__ import annotations

import string
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    KEYBOARD_PUNCTUATION_GLYPHS,
    KeyboardSymbolArena,
    MicroHaltCondition,
    MicroProgram,
    MicroProgramReductionScorer,
    MicroValueNode,
    UnboundSemanticError,
    reduce_micro_program,
)


def created_semantics(*, redundant_zero: bool = False) -> MicroProgram:
    zero = MicroValueNode("m_constant", constant=0)
    initial_zero = (
        MicroValueNode("m_add", (zero, zero)) if redundant_zero else zero
    )
    input_0 = MicroValueNode("m_input", index=0)
    input_1 = MicroValueNode("m_input", index=1)
    register_0 = MicroValueNode("m_register", index=0)
    register_1 = MicroValueNode("m_register", index=1)
    return MicroProgram(
        initial_registers=(initial_zero, input_1),
        halt_condition=MicroHaltCondition(1, 0),
        updates=(
            MicroValueNode("m_add", (register_0, input_0)),
            MicroValueNode(
                "m_add",
                (register_1, MicroValueNode("m_constant", constant=-1)),
            ),
        ),
        output_register=0,
    )


class KeyboardSymbolArenaTests(unittest.TestCase):
    def test_all_printable_punctuation_keys_start_unbound(self) -> None:
        arena = KeyboardSymbolArena()

        self.assertEqual(set(arena.glyphs), set(string.punctuation))
        self.assertEqual(arena.glyphs, KEYBOARD_PUNCTUATION_GLYPHS)
        self.assertEqual(len(arena.unbound_glyphs), 32)
        for glyph in ("+", "-", "*", "/", "="):
            with self.assertRaises(UnboundSemanticError):
                arena.execute(glyph, (2, 3))

    def test_verified_reward_winner_binds_one_opaque_glyph(self) -> None:
        arena = KeyboardSymbolArena()
        glyph, binding = arena.bind_reward_winner(
            created_semantics(), verification_status="bounded"
        )

        self.assertIn(glyph, string.punctuation)
        self.assertEqual(len(arena.bindings), 1)
        self.assertEqual(arena.execute(glyph, (7, 5)).output_value, 35.0)
        self.assertTrue(binding.operation_id.startswith("SEM-"))

    def test_reducer_preserves_semantics_and_simpler_original_gets_higher_reward(self) -> None:
        simple = created_semantics()
        redundant = created_semantics(redundant_zero=True)
        cases = (((2, 3), 6.0), ((7, 5), 35.0), ((11, 0), 0.0))
        scorer = MicroProgramReductionScorer()
        simple_score = scorer.score(simple, cases)
        redundant_score = scorer.score(redundant, cases)
        reduced = reduce_micro_program(redundant)

        self.assertTrue(simple_score.verified)
        self.assertTrue(redundant_score.verified)
        self.assertGreater(redundant_score.reduction_gain, 0)
        self.assertEqual(reduced.to_dict(), simple.to_dict())
        self.assertGreater(simple_score.reward, redundant_score.reward)

    def test_correctness_gate_dominates_short_incorrect_program(self) -> None:
        correct = created_semantics()
        incorrect = MicroProgram(
            initial_registers=(
                MicroValueNode("m_constant", constant=0),
                MicroValueNode("m_constant", constant=0),
            ),
            halt_condition=MicroHaltCondition(1, 0),
            updates=(
                MicroValueNode("m_register", index=0),
                MicroValueNode("m_register", index=1),
            ),
            output_register=0,
        )
        cases = (((2, 3), 6.0), ((7, 5), 35.0))
        scorer = MicroProgramReductionScorer()

        self.assertGreater(scorer.score(correct, cases).reward, scorer.score(incorrect, cases).reward)


if __name__ == "__main__":
    unittest.main()
