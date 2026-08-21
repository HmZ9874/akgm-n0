from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import (
    VerifiedEvolvedSemanticRoom,
    verify_evolved_operator,
    verify_evolved_operator_batch,
)
from akgm_n0.learner import InducedMicroOperator, OperatorEvolutionSearch


ROOT = Path(__file__).resolve().parents[1]


class OperatorEvolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seed_report = json.loads(
            (ROOT / "reports/data/ten_micro_operator_invention_latest.json").read_text(
                encoding="utf-8"
            )
        )
        cls.report = json.loads(
            (ROOT / "reports/data/hundred_operator_evolution_latest.json").read_text(
                encoding="utf-8"
            )
        )
        seeds = tuple(
            InducedMicroOperator.from_dict(item)
            for item in cls.seed_report["operators"]
        )
        cls.operators = OperatorEvolutionSearch().discover(
            seeds, requested_count=100, first_opcode=28
        )

    def test_same_hundred_unique_effects_are_recreated(self) -> None:
        self.assertEqual(len(self.operators), 100)
        self.assertEqual([item.opcode for item in self.operators], list(range(28, 128)))
        self.assertEqual(len({item.coefficient_vector for item in self.operators}), 100)
        self.assertEqual(
            [item.operator_id for item in self.operators],
            [item["operator_id"] for item in self.report["operators"]],
        )
        self.assertTrue(
            all(
                sum(value != 0 for value in item.coefficient_vector) >= 2
                for item in self.operators
            )
        )

    def test_all_symbolic_proofs_and_1200_replays_pass(self) -> None:
        proof = verify_evolved_operator_batch(self.operators, required_count=100)
        self.assertTrue(proof["passed"])
        self.assertEqual(sum(item["passed"] for item in proof["operator_results"]), 100)
        self.assertEqual(proof["passed_probe_case_count"], 1200)
        self.assertEqual(proof["probe_case_count"], 1200)

    def test_coefficient_mutation_is_rejected(self) -> None:
        original = self.operators[0]
        mutated = replace(
            original,
            coefficient_vector=(99,) + original.coefficient_vector[1:],
        )
        proof = verify_evolved_operator(mutated)
        self.assertFalse(proof["passed"])
        self.assertFalse(
            next(
                item for item in proof["obligations"]
                if item["obligation_id"] == "instruction_symbolic_vector_binding"
            )["passed"]
        )

    def test_hundred_semantics_form_a_replayable_hash_chain(self) -> None:
        proof = verify_evolved_operator_batch(self.operators, required_count=100)
        by_id = {item["operator_id"]: item for item in proof["operator_results"]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evolved.jsonl"
            room = VerifiedEvolvedSemanticRoom(path)
            for operator in self.operators:
                room.record(operator, by_id[operator.operator_id])
            reloaded = VerifiedEvolvedSemanticRoom(path)
            self.assertEqual(len(reloaded.records), 100)
            self.assertEqual(reloaded.records[0]["previous_event_hash"], "0" * 64)
            self.assertEqual(
                reloaded.records[-1]["operator"]["operator_id"],
                self.operators[-1].operator_id,
            )


if __name__ == "__main__":
    unittest.main()
