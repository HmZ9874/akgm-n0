from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import (
    ReversibleFoundationRoom,
    verify_reversible_foundation_semantic,
)
from akgm_n0.learner import (
    MultiTapeExecutor,
    ReversibleFoundationSemantic,
    ReversibleTapeSearch,
    TokenExample,
    opaque_symbols,
    unary_marks,
)


ROOT = Path(__file__).resolve().parents[1]


class ReversibleTapeFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/reversible_cancellation_latest.json").read_text(encoding="utf-8")
        )
        cls.semantic = ReversibleFoundationSemantic.from_dict(
            cls.report["discovery"]["semantic"]
        )

    def test_anonymous_search_recreates_unique_two_phase_program(self) -> None:
        examples = tuple(
            TokenExample(
                (opaque_symbols("X", left), opaque_symbols("Y", right)),
                unary_marks(max(left - right, 0)),
            )
            for left, right in ((0, 0), (1, 0), (0, 1), (2, 1), (1, 2), (3, 3), (7, 2), (2, 7), (9, 4))
        )
        result = ReversibleTapeSearch().search("TEST-CANCEL", 2, examples, maximum_phases=2)
        self.assertEqual(result.candidates_evaluated, 43)
        self.assertEqual(sum(item.exact for item in result.candidates), 1)
        self.assertEqual(result.selected.program.program_id, self.semantic.program.program_id)
        self.assertEqual(len(result.selected.program.phases), 2)

    def test_universal_proof_and_hidden_replays_pass(self) -> None:
        proof = verify_reversible_foundation_semantic(self.semantic)
        self.assertTrue(proof["passed"])
        self.assertEqual(sum(item["passed"] for item in proof["obligations"]), 11)
        self.assertEqual(sum(item["passed"] for item in proof["case_results"]), 10)
        self.assertEqual(proof["not_claimed"], "integer subtraction or negative-number representation")

    def test_reversed_inputs_do_not_fake_a_negative_number(self) -> None:
        execution = MultiTapeExecutor().execute(
            self.semantic.program,
            (opaque_symbols("X", 2), opaque_symbols("Y", 7)),
        )
        self.assertTrue(execution.halted)
        self.assertEqual(execution.output, ())

    def test_tampered_phase_claim_is_rejected(self) -> None:
        mutated_program = replace(
            self.semantic.program,
            phases=(self.semantic.program.phases[1], self.semantic.program.phases[0]),
        )
        proof = verify_reversible_foundation_semantic(
            replace(self.semantic, program=mutated_program)
        )
        self.assertFalse(proof["passed"])

    def test_success_room_replays_proof(self) -> None:
        room = ReversibleFoundationRoom(
            ROOT / "artifacts/foundation/success/reversible_semantics.jsonl"
        )
        self.assertEqual(len(room.records), 1)
        self.assertEqual(
            room.records[0]["semantic"]["semantic_id"],
            "RSEM-6082532054ec1e05",
        )


if __name__ == "__main__":
    unittest.main()
