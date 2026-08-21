from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import (
    FormulaRejectionRoom,
    VerifiedEvolvedSemanticRoom,
    verify_evolved_operator,
    verify_mass_formula_batch,
)
from akgm_n0.learner import InducedMicroOperator, OperatorEvolutionSearch


ROOT = Path(__file__).resolve().parents[1]


class ThousandParametricFormulaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        seed_report = json.loads(
            (ROOT / "reports/data/ten_micro_operator_invention_latest.json").read_text(encoding="utf-8")
        )
        prior_report = json.loads(
            (ROOT / "reports/data/hundred_operator_evolution_latest.json").read_text(encoding="utf-8")
        )
        cls.report = json.loads(
            (ROOT / "reports/data/thousand_parametric_formulas_latest.json").read_text(encoding="utf-8")
        )
        cls.prior_vectors = tuple(tuple(item["coefficient_vector"]) for item in prior_report["operators"])
        seeds = tuple(InducedMicroOperator.from_dict(item) for item in seed_report["operators"])
        cls.formulas = OperatorEvolutionSearch().discover(
            seeds,
            requested_count=1000,
            first_opcode=132,
            excluded_coefficient_vectors=cls.prior_vectors,
            generation=3,
        )

    def test_same_thousand_novel_semantics_are_recreated(self) -> None:
        self.assertEqual(len(self.formulas), 1000)
        self.assertEqual([item.opcode for item in self.formulas], list(range(132, 1132)))
        self.assertEqual(len({item.coefficient_vector for item in self.formulas}), 1000)
        self.assertFalse({item.coefficient_vector for item in self.formulas} & set(self.prior_vectors))
        self.assertEqual(
            [item.operator_id for item in self.formulas],
            [item["operator_id"] for item in self.report["formulas"]],
        )

    def test_all_exact_proofs_and_twelve_thousand_replays_pass(self) -> None:
        proof = verify_mass_formula_batch(
            self.formulas,
            prior_coefficient_vectors=self.prior_vectors,
        )
        self.assertTrue(proof["passed"])
        self.assertEqual(proof["formula_proof_count"], 1000)
        self.assertEqual(proof["hidden_replay_passed_count"], 12000)
        self.assertEqual(proof["hidden_replay_count"], 12000)

    def test_false_semantic_claim_is_rejected(self) -> None:
        original = self.formulas[0]
        mutated = replace(
            original,
            coefficient_vector=(original.coefficient_vector[0] + 1, *original.coefficient_vector[1:]),
        )
        proof = verify_evolved_operator(mutated)
        self.assertFalse(proof["passed"])
        self.assertIn(
            "instruction_symbolic_vector_binding",
            [item["obligation_id"] for item in proof["obligations"] if not item["passed"]],
        )

    def test_success_and_mistake_rooms_replay(self) -> None:
        successes = VerifiedEvolvedSemanticRoom(
            ROOT / "artifacts/formula_rooms/mass_universal/proven_formulas.jsonl"
        )
        mistakes = FormulaRejectionRoom(
            ROOT / "artifacts/formula_rooms/mistakes/thousand_formula_rejections.jsonl"
        )
        self.assertEqual(len(successes.records), 1000)
        self.assertGreaterEqual(len(mistakes.records), 102)
        self.assertTrue(all(item["verification"]["passed"] for item in successes.records))


if __name__ == "__main__":
    unittest.main()

