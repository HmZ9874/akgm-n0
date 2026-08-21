from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from akgm_n0.evaluator.autonomous_operator_research_v7 import verify_autonomous_operator_research_v7
from akgm_n0.evaluator.autonomous_operator_room_v7 import AutonomousOperatorV7Room
from akgm_n0.learner.autonomous_operator_research_v7 import (
    DiscoveredOperator,
    expression_for_support,
    symbolic_normal_form,
)


ROOT = Path(__file__).resolve().parents[1]


class AutonomousOperatorResearchV7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.persisted = json.loads(
            (ROOT / "reports/data/autonomous_operator_research_v7_500_latest.json").read_text(encoding="utf-8")
        )
        cls.research = cls.persisted["research"]

    def test_exactly_five_hundred_three_way_distinct_operators(self) -> None:
        self.assertTrue(self.research["passed"])
        self.assertEqual(self.research["promoted_operator_count"], 500)
        self.assertEqual(self.research["unique_program_count"], 500)
        self.assertEqual(self.research["unique_support_count"], 500)
        self.assertEqual(self.research["unique_behavior_count"], 500)

    def test_parameter_and_coefficient_padding_are_forbidden(self) -> None:
        for record in self.research["operators"]:
            normal = record["normal_form"]
            self.assertTrue(all(coefficient == 1 for _, _, coefficient in normal))
            self.assertTrue(all(x_degree or y_degree for x_degree, y_degree, _ in normal))
        novelty = self.research["novelty_contract"]
        self.assertFalse(novelty["constant_variants_counted"])
        self.assertFalse(novelty["coefficient_variants_counted"])
        self.assertFalse(novelty["same_monomial_support_variants_counted"])

    def test_research_was_target_free_and_claim_is_bounded(self) -> None:
        self.assertFalse(self.research["research_received_target_formulas"])
        self.assertEqual(self.research["novelty_contract"]["foundational_operator_count"], 0)
        self.assertEqual(self.research["novelty_contract"]["derived_operator_count"], 500)

    def test_all_proofs_replay_and_tampering_fails(self) -> None:
        self.assertTrue(verify_autonomous_operator_research_v7(self.research)["passed"])
        forged = json.loads(json.dumps(self.research))
        forged["operators"][0]["normal_form"][0][2] = 2
        self.assertFalse(verify_autonomous_operator_research_v7(forged)["passed"])

    def test_alternative_order_reduces_to_same_normal_form(self) -> None:
        item = DiscoveredOperator.from_dict(self.research["operators"][123])
        support = tuple((x, y) for x, y, _ in item.normal_form)
        alternative = expression_for_support(support, reverse=True)
        self.assertEqual(symbolic_normal_form(alternative), item.normal_form)

    def test_success_room_replays_all_five_hundred(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operators.jsonl"
            room = AutonomousOperatorV7Room(path)
            for record in self.research["operators"]:
                room.record(record)
            self.assertEqual(len(AutonomousOperatorV7Room(path).records), 500)


if __name__ == "__main__":
    unittest.main()
