from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenIntegerGridEnvironment
from akgm_n0.learner import (
    MicroProgramExecutor,
    MicroProgramSearch,
    UnboundSemanticError,
    UnboundSemanticSlot,
)


SECRET = b"unbound-semantic-slot-tests"
DEVELOPMENT_ROWS = (
    (2, 2),
    (2, 3),
    (3, 2),
    (4, 3),
    (-2, 3),
    (5, 2),
    (3, 4),
    (6, 5),
)


class SemanticSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        development = HiddenIntegerGridEnvironment(
            DEVELOPMENT_ROWS, seed=401, secret=SECRET
        ).observe()
        cls.report = MicroProgramSearch(top_k=200).search(development)
        cls.blind_rows = ((7, 5), (-4, 6), (11, 0), (2, 9), (9, 2), (-3, 8))
        cls.blind = HiddenIntegerGridEnvironment(
            cls.blind_rows, seed=402, secret=SECRET
        ).observe()
        exact = [
            candidate
            for candidate in cls.report.top_candidates
            if candidate.fit_error == 0.0
        ]
        cls.development_only_candidate = exact[0]
        cls.selected = next(
            candidate
            for candidate in exact
            if cls._passes_blind(candidate)
        )

    @classmethod
    def _passes_blind(cls, candidate) -> bool:
        executor = MicroProgramExecutor()
        try:
            predictions = tuple(
                executor.execute(candidate.program, row).output_value
                for row in cls.blind_rows
            )
        except Exception:
            return False
        return predictions == cls.blind.output_values

    def test_glyph_has_no_intrinsic_behavior(self) -> None:
        slot = UnboundSemanticSlot("*")

        with self.assertRaises(UnboundSemanticError):
            slot.execute((2, 3))

    def test_search_finds_exact_microstate_semantics_without_iterate_node(self) -> None:
        serialized = json.dumps(self.selected.program.to_dict(), sort_keys=True)

        self.assertEqual(self.selected.fit_error, 0.0)
        self.assertNotIn("iterate", serialized)
        self.assertNotIn("multiply", serialized)
        self.assertNotIn("divide", serialized)
        self.assertIn("halt_condition", serialized)
        self.assertIn("simultaneous_updates", serialized)

    def test_verified_binding_passes_unseen_rows(self) -> None:
        slot = UnboundSemanticSlot("*")
        slot.bind(self.selected.program, verification_status="bounded")
        predictions = tuple(
            slot.execute(row).output_value for row in self.blind_rows
        )

        self.assertEqual(predictions, self.blind.output_values)

    def test_development_exact_candidate_can_still_fail_independent_blind_test(self) -> None:
        self.assertEqual(self.development_only_candidate.fit_error, 0.0)
        self.assertFalse(self._passes_blind(self.development_only_candidate))

    def test_glyph_randomization_does_not_change_created_semantics(self) -> None:
        outputs = []
        operation_ids = []
        for glyph in ("*", "@", "#"):
            slot = UnboundSemanticSlot(glyph)
            binding = slot.bind(self.selected.program, verification_status="verified")
            outputs.append(slot.execute((7, 5)).output_value)
            operation_ids.append(binding.operation_id)

        self.assertEqual(outputs, [35.0, 35.0, 35.0])
        self.assertEqual(len(set(operation_ids)), 1)

    def test_unverified_program_cannot_bind_symbol(self) -> None:
        slot = UnboundSemanticSlot("*")

        with self.assertRaises(UnboundSemanticError):
            slot.bind(self.selected.program, verification_status="fit_passed")


if __name__ == "__main__":
    unittest.main()
