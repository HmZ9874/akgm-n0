from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import (
    UniversalFormulaRoom,
    VerifiedSemanticRoom,
    verify_micro_operator,
    verify_micro_operator_batch,
)
from akgm_n0.learner import MicroOperatorMiner


ROOT = Path(__file__).resolve().parents[1]


def proven_sources():
    sources = []
    seen = set()
    for relative in (
        "artifacts/formula_rooms/universal/proven_formulas.jsonl",
        "artifacts/formula_rooms/parametric/proven_formulas.jsonl",
    ):
        for record in UniversalFormulaRoom(ROOT / relative).records:
            if record.room_record_id in seen or "words" not in record.program:
                continue
            seen.add(record.room_record_id)
            sources.append((record.room_record_id, tuple(record.program["words"])))
    return sources


class MicroOperatorMiningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/ten_micro_operator_invention_latest.json").read_text(
                encoding="utf-8"
            )
        )
        cls.operators = MicroOperatorMiner().discover(
            proven_sources(), requested_count=10, first_opcode=18, minimum_occurrences=2
        )

    def test_exact_same_ten_semantics_are_reinduced_without_labels(self) -> None:
        self.assertEqual(len(self.operators), 10)
        self.assertEqual([item.opcode for item in self.operators], list(range(18, 28)))
        self.assertEqual(
            [item.operator_id for item in self.operators],
            [item["operator_id"] for item in self.report["operators"]],
        )
        self.assertEqual(len({item.effect_signature for item in self.operators}), 10)
        self.assertTrue(all(len(item.source_record_ids) >= 2 for item in self.operators))

    def test_independent_expansion_replay_passes_all_120_cases(self) -> None:
        proof = verify_micro_operator_batch(self.operators, required_count=10)
        self.assertTrue(proof["passed"])
        self.assertEqual(proof["passed_probe_case_count"], 120)
        self.assertEqual(proof["probe_case_count"], 120)

    def test_effect_mutation_is_rejected(self) -> None:
        original = self.operators[0]
        mutated = replace(original, effect_ast={"op": "token", "token": "cell:0"})
        proof = verify_micro_operator(mutated)
        self.assertFalse(proof["passed"])
        self.assertFalse(
            next(
                item for item in proof["obligations"]
                if item["obligation_id"] == "effect_signature_binding"
            )["passed"]
        )

    def test_verified_semantic_room_is_hash_chained_and_replayable(self) -> None:
        proof = verify_micro_operator_batch(self.operators, required_count=10)
        by_id = {item["operator_id"]: item for item in proof["operator_results"]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "semantics.jsonl"
            room = VerifiedSemanticRoom(path)
            for operator in self.operators:
                room.record(operator, by_id[operator.operator_id])
            reloaded = VerifiedSemanticRoom(path)
            self.assertEqual(len(reloaded.records), 10)
            self.assertEqual(reloaded.records[0]["previous_event_hash"], "0" * 64)
            self.assertEqual(
                reloaded.records[-1]["operator"]["operator_id"],
                self.operators[-1].operator_id,
            )


if __name__ == "__main__":
    unittest.main()
