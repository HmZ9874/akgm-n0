from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import (
    DirectionalFoundationRoom,
    verify_directional_foundation_semantic,
)
from akgm_n0.learner import (
    DirectionalFoundationSemantic,
    DirectionalTapeSearch,
    MultiTapeExecutor,
    TokenExample,
    decode_signed_unary,
    opaque_symbols,
    signed_unary_output,
)


ROOT = Path(__file__).resolve().parents[1]


class DirectionalFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/directional_difference_latest.json").read_text(encoding="utf-8")
        )
        cls.semantic = DirectionalFoundationSemantic.from_dict(
            cls.report["discovery"]["semantic"]
        )

    def test_search_recreates_two_equally_valid_directional_programs(self) -> None:
        examples = tuple(
            TokenExample(
                (opaque_symbols("A", left), opaque_symbols("B", right)),
                signed_unary_output(left, right),
            )
            for left, right in ((0, 0), (1, 0), (0, 1), (2, 1), (1, 2), (3, 3), (7, 2), (2, 7), (9, 4), (4, 9), (11, 3), (3, 11))
        )
        result = DirectionalTapeSearch().search("TEST-DIRECTION", examples)
        self.assertEqual(result.candidates_evaluated, 820)
        exact = [item for item in result.candidates if item.exact]
        self.assertEqual(len(exact), 2)
        self.assertEqual(len({item.reward for item in exact}), 1)
        self.assertEqual(result.selected.program.program_id, self.semantic.program.program_id)

    def test_proof_and_negative_direction_hidden_cases_pass(self) -> None:
        proof = verify_directional_foundation_semantic(self.semantic)
        self.assertTrue(proof["passed"])
        self.assertEqual(sum(item["passed"] for item in proof["obligations"]), 14)
        self.assertEqual(sum(item["passed"] for item in proof["case_results"]), 12)
        self.assertLess(min(item["decoded_value"] for item in proof["case_results"]), 0)

    def test_alternate_glyph_decodes_as_negative_direction(self) -> None:
        execution = MultiTapeExecutor().execute(
            self.semantic.program,
            (opaque_symbols("A", 2), opaque_symbols("B", 7)),
        )
        self.assertEqual(decode_signed_unary(execution.output), -5)
        self.assertEqual(execution.output, signed_unary_output(2, 7))

    def test_tampered_phase_order_claim_without_recompile_is_rejected(self) -> None:
        phases = self.semantic.program.phases
        mutated = replace(
            self.semantic,
            program=replace(self.semantic.program, phases=(phases[1], phases[0], phases[2])),
        )
        self.assertFalse(verify_directional_foundation_semantic(mutated)["passed"])

    def test_directional_room_replays(self) -> None:
        room = DirectionalFoundationRoom(
            ROOT / "artifacts/foundation/success/directional_semantics.jsonl"
        )
        self.assertEqual(len(room.records), 1)
        self.assertEqual(room.records[0]["semantic"]["semantic_id"], "DSEM-be8bf9c60762e0f0")


if __name__ == "__main__":
    unittest.main()
