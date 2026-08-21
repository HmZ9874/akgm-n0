from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import FoundationSemanticRoom, verify_foundation_semantic
from akgm_n0.learner import (
    AnonymousTokenTask,
    FoundationProgramSearch,
    FoundationSemantic,
    TokenExample,
    ZeroArithmeticExecutor,
    opaque_symbols,
    unary_marks,
)


ROOT = Path(__file__).resolve().parents[1]


class FoundationKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/zero_arithmetic_foundation_latest.json").read_text(encoding="utf-8")
        )
        cls.semantics = tuple(
            FoundationSemantic.from_dict(item["semantic"])
            for item in cls.report["discoveries"]
        )

    def test_kernel_program_discovers_single_source_transfer(self) -> None:
        task = AnonymousTokenTask(
            "TEST-OPAQUE",
            1,
            tuple(
                TokenExample((opaque_symbols("x", length),), unary_marks(length))
                for length in (0, 1, 4, 9)
            ),
        )
        search = FoundationProgramSearch().search(task)
        self.assertTrue(search.selected.exact)
        self.assertEqual(search.selected.program.source_plan, (0,))
        self.assertEqual(
            ZeroArithmeticExecutor().execute(
                search.selected.program, (opaque_symbols("z", 23),)
            ).output,
            unary_marks(23),
        )

    def test_two_foundation_semantics_have_no_arithmetic_opcode_and_pass_proof(self) -> None:
        self.assertEqual(len(self.semantics), 2)
        for semantic in self.semantics:
            self.assertTrue(
                all(instruction.opcode in {0, 1, 2, 3, 4} for instruction in semantic.program.instructions)
            )
            proof = verify_foundation_semantic(semantic)
            self.assertTrue(proof["passed"])
            self.assertFalse(proof["finite_sampling_used_as_proof"])
        self.assertEqual(self.semantics[1].dependency_semantic_ids, (self.semantics[0].semantic_id,))

    def test_false_structure_claim_is_rejected(self) -> None:
        semantic = self.semantics[1]
        mutated = replace(semantic, source_slots=(0,))
        proof = verify_foundation_semantic(mutated)
        self.assertFalse(proof["passed"])
        self.assertIn(
            "canonical_program_binding",
            [item["obligation_id"] for item in proof["obligations"] if not item["passed"]],
        )

    def test_foundation_room_replays_and_composites_do_not_count(self) -> None:
        room = FoundationSemanticRoom(
            ROOT / "artifacts/foundation/success/foundation_semantics.jsonl"
        )
        self.assertEqual(len(room.records), 2)
        self.assertTrue(all(item["proof"]["passed"] for item in room.records))
        composite = self.report["capability_graph"]["composite_formula_library"]
        self.assertEqual(composite["record_count"], 1000)
        self.assertFalse(composite["counts_as_foundational_discovery"])


if __name__ == "__main__":
    unittest.main()
