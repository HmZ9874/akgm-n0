from __future__ import annotations

import json
import unittest
from pathlib import Path

from akgm_n0.evaluator import UniversalFormulaRoom, verify_repeat_macro_semantic
from akgm_n0.learner import RepeatMacroExecutor, RepeatMacroInducer


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


class RepeatMacroInventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/repeat_macro_latest.json").read_text(encoding="utf-8")
        )
        cls.semantic = RepeatMacroInducer().induce(
            sources(), occupied_opcodes=tuple(range(16, 131))
        )

    def test_same_generic_macro_is_reinduced_from_many_bodies(self) -> None:
        self.assertEqual(self.semantic.opcode, 131)
        self.assertEqual(self.semantic.semantic_id, "SEM-ea6d06e2e7226d79")
        self.assertEqual(len(self.semantic.source_record_ids), 30)
        self.assertEqual(len(self.semantic.occurrences), 33)
        self.assertEqual(len(self.semantic.observed_body_shapes), 20)

    def test_universal_induction_and_expansion_proof_pass(self) -> None:
        proof = verify_repeat_macro_semantic(self.semantic)
        self.assertTrue(proof["passed"])
        self.assertEqual(sum(item["passed"] for item in proof["obligations"]), 8)
        self.assertEqual(sum(item["passed"] for item in proof["case_results"]), 20)

    def test_body_is_a_runtime_parameter_and_zero_count_is_identity(self) -> None:
        executor = RepeatMacroExecutor()
        identity = executor.execute((7, 11), 0, lambda state: (999,))
        self.assertEqual(identity.final_state, (7, 11))
        result = executor.execute((1, 1), 10, lambda state: (state[1], state[0] + state[1]))
        self.assertEqual(result.final_state, (89, 144))
        with self.assertRaises(ValueError):
            executor.execute((1,), -1, lambda state: state)

    def test_macro_is_in_control_semantic_success_room(self) -> None:
        events = [
            json.loads(line) for line in (
                ROOT / "artifacts/semantics/verified_control_semantics.jsonl"
            ).read_text(encoding="utf-8").splitlines() if line
        ]
        self.assertTrue(
            any(item["semantic"]["semantic_id"] == self.semantic.semantic_id for item in events)
        )


if __name__ == "__main__":
    unittest.main()
