from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import UniversalSemanticAuditLoop
from akgm_n0.learner import EvolvedMicroOperator


ROOT = Path(__file__).resolve().parents[1]


class UniversalSemanticAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(
            (ROOT / "reports/data/hundred_operator_evolution_latest.json").read_text(
                encoding="utf-8"
            )
        )
        cls.report = json.loads(
            (ROOT / "reports/data/universal_semantic_audit_latest.json").read_text(
                encoding="utf-8"
            )
        )
        cls.operators = tuple(
            EvolvedMicroOperator.from_dict(item) for item in cls.source["operators"]
        )

    def test_hundred_semantics_reach_a_two_round_proven_fixed_point(self) -> None:
        result = UniversalSemanticAuditLoop().run(self.operators)
        self.assertTrue(result["converged"])
        self.assertEqual(len(result["rounds"]), 2)
        self.assertEqual(len(result["active_operators"]), 100)
        self.assertEqual(len(result["rejected"]), 0)
        self.assertTrue(all(item["passed"] for item in result["active_audits"]))

    def test_corrupted_semantic_is_removed_and_loop_converges(self) -> None:
        first = self.operators[0]
        corrupted = replace(
            first, coefficient_vector=(999,) + first.coefficient_vector[1:]
        )
        result = UniversalSemanticAuditLoop().run((corrupted,))
        self.assertTrue(result["converged"])
        self.assertEqual(len(result["active_operators"]), 0)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertFalse(result["rejected"][0]["audit"]["passed"])

    def test_domain_contract_does_not_overclaim_natural_number_closure(self) -> None:
        proof = self.report["proof_summary"]
        self.assertEqual(proof["natural_number_safe_without_subtraction_count"], 28)
        self.assertEqual(proof["requires_additive_inverse_count"], 72)
        self.assertEqual(proof["obligations_passed"], 500)
        self.assertEqual(proof["obligations_total"], 500)

    def test_active_catalog_contains_only_passed_audits(self) -> None:
        catalog = json.loads(
            (ROOT / "artifacts/semantics/active_evolved_semantics.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(catalog["active_count"], 100)
        self.assertTrue(
            all(item["universal_audit"]["passed"] for item in catalog["operators"])
        )


if __name__ == "__main__":
    unittest.main()
