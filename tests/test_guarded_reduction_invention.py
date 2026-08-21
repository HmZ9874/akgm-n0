from __future__ import annotations

import json
import unittest
from pathlib import Path

from akgm_n0.evaluator import UniversalFormulaRoom, verify_guarded_reduction_semantic
from akgm_n0.learner import GuardedReductionExecutor, GuardedReductionOpcodeInducer


ROOT = Path(__file__).resolve().parents[1]


def sources():
    result = []
    seen = set()
    for relative in (
        "artifacts/formula_rooms/universal/proven_formulas.jsonl",
        "artifacts/formula_rooms/parametric/proven_formulas.jsonl",
    ):
        for record in UniversalFormulaRoom(ROOT / relative).records:
            if record.room_record_id in seen or "words" not in record.program:
                continue
            seen.add(record.room_record_id)
            result.append((record.room_record_id, tuple(record.program["words"])))
    return result


class GuardedReductionInventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/guarded_reduction_operator_latest.json").read_text(
                encoding="utf-8"
            )
        )
        cls.semantic = GuardedReductionOpcodeInducer().induce(
            sources(), occupied_opcodes=tuple(range(16, 128))
        )

    def test_same_control_semantic_is_reinduced_without_formula_labels(self) -> None:
        self.assertEqual(self.semantic.opcode, 128)
        self.assertEqual(self.semantic.semantic_id, "SEM-61440ea9651ce7ba")
        self.assertEqual(len(self.semantic.source_record_ids), 3)
        self.assertEqual(
            self.semantic.semantic_id,
            self.report["invented_operator"]["semantic_id"],
        )

    def test_universal_proof_and_hidden_replay_pass(self) -> None:
        proof = verify_guarded_reduction_semantic(self.semantic)
        self.assertTrue(proof["passed"])
        self.assertEqual(sum(item["passed"] for item in proof["obligations"]), 8)
        self.assertEqual(sum(item["passed"] for item in proof["case_results"]), 56)

    def test_executor_has_data_dependent_iteration_and_exact_exit(self) -> None:
        result = GuardedReductionExecutor().execute(17, 0, 5)
        self.assertEqual(result.final_count, 3)
        self.assertEqual(result.final_remainder, 2)
        self.assertEqual(result.iteration_count, 3)
        with self.assertRaises(ValueError):
            GuardedReductionExecutor().execute(17, 0, 0)

    def test_control_semantic_success_room_contains_operator(self) -> None:
        events = [
            json.loads(line)
            for line in (
                ROOT / "artifacts/semantics/verified_control_semantics.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line
        ]
        self.assertTrue(
            any(item["semantic"]["semantic_id"] == self.semantic.semantic_id for item in events)
        )


if __name__ == "__main__":
    unittest.main()
