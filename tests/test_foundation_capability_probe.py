from __future__ import annotations

import json
import unittest
from pathlib import Path

from akgm_n0.learner import (
    AnonymousTokenTask,
    FoundationProgramSearch,
    TokenExample,
    ZeroArithmeticExecutor,
    opaque_symbols,
    unary_marks,
)


ROOT = Path(__file__).resolve().parents[1]


class FoundationCapabilityProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/foundation_capability_probe_latest.json").read_text(encoding="utf-8")
        )

    def test_blind_probe_transfers_only_conservation_family(self) -> None:
        self.assertEqual(self.report["summary"]["transferred_task_count"], 3)
        self.assertEqual(self.report["summary"]["failed_task_count"], 3)
        self.assertEqual(self.report["summary"]["new_foundation_count"], 0)
        statuses = {item["posthoc_evaluator_label"]: item["status"] for item in self.report["results"]}
        self.assertEqual(statuses["three_collection_conservation"], "transferred")
        self.assertEqual(statuses["one_sided_pair_cancellation"], "outside_current_program_language")
        self.assertEqual(statuses["rectangular_repetition"], "outside_current_program_language")
        self.assertEqual(statuses["equal_group_extraction"], "outside_current_program_language")

    def test_order_invariance_is_observed_without_new_foundation_claim(self) -> None:
        two = self.report["results"][1]
        three = self.report["results"][2]
        self.assertEqual(two["development"]["minimum_exact_program_count"], 2)
        self.assertEqual(three["development"]["minimum_exact_program_count"], 6)
        self.assertFalse(any(item["new_foundation"] for item in self.report["discovered_properties"]))

    def test_current_language_can_only_emit_conserved_source_subsets(self) -> None:
        task = AnonymousTokenTask(
            "BOUNDARY",
            2,
            (TokenExample((opaque_symbols("a", 3), opaque_symbols("b", 5)), unary_marks(0)),),
        )
        candidates = FoundationProgramSearch().enumerate_candidates(task)
        observed = {
            len(ZeroArithmeticExecutor().execute(item.program, task.examples[0].sources).output)
            for item in candidates
        }
        self.assertEqual(observed, {0, 3, 5, 8})
        self.assertNotIn(15, observed)
        self.assertNotIn(1, observed)


if __name__ == "__main__":
    unittest.main()
