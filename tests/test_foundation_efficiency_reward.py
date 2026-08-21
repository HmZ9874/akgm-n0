from __future__ import annotations

import json
import unittest
from pathlib import Path

from akgm_n0.learner import (
    AnonymousTokenTask,
    FoundationProgramSearch,
    TokenExample,
    opaque_symbols,
    unary_marks,
)


ROOT = Path(__file__).resolve().parents[1]


class FoundationEfficiencyRewardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/foundation_efficiency_reward_latest.json").read_text(encoding="utf-8")
        )

    def test_all_reward_gates_pass(self) -> None:
        self.assertTrue(all(item["passed"] for item in self.report["gates"]))
        self.assertEqual(
            self.report["policy"]["macro_accounting"],
            "charge expanded primitive execution, not only the macro call",
        )

    def test_lower_token_exact_program_has_higher_reward(self) -> None:
        for comparison in self.report["comparisons"]:
            self.assertGreater(comparison["token_reduction"], 0)
            self.assertEqual(comparison["reward_gain"], comparison["token_reduction"])
            self.assertGreater(comparison["selected_reward"], comparison["redundant_reward"])

    def test_incorrect_short_program_is_not_promotable(self) -> None:
        control = self.report["cheap_incorrect_control"]
        self.assertFalse(control["exact"])
        self.assertLess(
            control["reward"],
            self.report["equal_efficiency_order_control"]["selected"]["reward"],
        )

    def test_search_candidate_exposes_honest_token_accounting(self) -> None:
        task = AnonymousTokenTask(
            "REWARD-TEST",
            1,
            tuple(
                TokenExample((opaque_symbols("x", length),), unary_marks(length))
                for length in (0, 1, 3)
            ),
        )
        candidates = FoundationProgramSearch().enumerate_candidates(task)
        minimal = next(item for item in candidates if item.program.source_plan == (0,))
        redundant = next(item for item in candidates if item.program.source_plan == (0, 0))
        self.assertTrue(minimal.exact and redundant.exact)
        self.assertEqual(minimal.total_token_cost, minimal.execution_token_cost + minimal.program_token_cost)
        self.assertGreater(minimal.reward, redundant.reward)


if __name__ == "__main__":
    unittest.main()
