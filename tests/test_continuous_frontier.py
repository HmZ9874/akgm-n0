from __future__ import annotations

import json
import unittest
from fractions import Fraction
from pathlib import Path

from akgm_n0.evaluator import verify_continuous_semantics
from akgm_n0.learner import (
    LocalSample,
    LocalStabilitySemantic,
    PartitionAccumulationSemantic,
    PartitionSample,
)


ROOT = Path(__file__).resolve().parents[1]


class ContinuousFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/continuous_frontier_latest.json").read_text(
                encoding="utf-8"
            )
        )
        cls.local = LocalStabilitySemantic.from_dict(
            cls.report["discovered_semantics"][0]["semantic"]
        )
        cls.partition = PartitionAccumulationSemantic.from_dict(
            cls.report["discovered_semantics"][1]["semantic"]
        )

    def test_selected_semantics_have_stable_ids_and_no_target_labels(self) -> None:
        self.assertEqual(self.local.semantic_id, "SEM-40d50eb6008bf37f")
        self.assertEqual(self.partition.semantic_id, "SEM-11a96cb9aa1e206d")
        self.assertEqual((self.local.opcode, self.partition.opcode), (129, 130))
        self.assertEqual(self.report["exploration_scale"]["total_candidate_count"], 132)
        self.assertFalse(self.report["learner_received"]["calculus_terms"])
        self.assertFalse(self.report["learner_received"]["target_outputs"])

    def test_independent_polynomial_domain_proof_passes(self) -> None:
        proof = verify_continuous_semantics(self.local, self.partition)
        self.assertTrue(proof["passed"])
        self.assertEqual(sum(item["passed"] for item in proof["obligations"]), 10)
        self.assertTrue(proof["counterexample"]["rejected"])

    def test_local_semantic_is_exact_on_anonymous_linear_world(self) -> None:
        point = Fraction(7, 3)
        step = Fraction(1, 1024)
        function = lambda value: 5 * value - 11
        forward, backward = self.local.execute(
            LocalSample("linear", point, step, function(point-step), function(point), function(point+step))
        )
        self.assertEqual(forward, 5)
        self.assertEqual(backward, 5)

    def test_partition_semantic_accumulates_constant_world_exactly(self) -> None:
        start, end, count = Fraction(0), Fraction(3), 12
        values = (Fraction(2),) * count
        sample = PartitionSample("constant", "interval", start, end, count, values, values, values)
        self.assertEqual(self.partition.execute(sample), 6)

    def test_success_and_mistake_rooms_are_persisted(self) -> None:
        semantic_events = [
            json.loads(line) for line in (
                ROOT / "artifacts/semantics/verified_continuous_semantics.jsonl"
            ).read_text(encoding="utf-8").splitlines() if line
        ]
        mistake_events = [
            json.loads(line) for line in (
                ROOT / "artifacts/mistakes/continuous_frontier_mistakes.jsonl"
            ).read_text(encoding="utf-8").splitlines() if line
        ]
        self.assertEqual(len(semantic_events), 2)
        self.assertGreaterEqual(len(mistake_events), 1)


if __name__ == "__main__":
    unittest.main()
