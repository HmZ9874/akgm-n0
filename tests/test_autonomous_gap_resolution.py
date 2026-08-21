from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import DistinctFrontierRoom, verify_distinct_foundation_semantic
from akgm_n0.learner import (
    DistinctExample,
    DistinctExecutor,
    DistinctExpansionSearch,
    DistinctFoundationSemantic,
    distinct_word_observation,
    opaque_symbols,
)


ROOT = Path(__file__).resolve().parents[1]


class AutonomousGapResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/autonomous_gap_resolution_latest.json").read_text(encoding="utf-8")
        )
        cls.semantic = DistinctFoundationSemantic.from_dict(cls.report["discovery"]["semantic"])

    def test_search_selects_one_full_record_memory_program(self) -> None:
        examples = []
        for index, (base_count, control_count) in enumerate(
            ((0, 0), (1, 2), (2, 2), (2, 3), (3, 2), (3, 3), (4, 3))
        ):
            base = opaque_symbols(f"B{index}", base_count)
            control = opaque_symbols(f"C{index}", control_count)
            examples.append(DistinctExample((base, control), distinct_word_observation(base, control)))
        search = DistinctExpansionSearch().search("TEST-GAP", examples)
        self.assertEqual(search.candidates_evaluated, 48)
        self.assertEqual(sum(item.exact for item in search.candidates), 1)
        self.assertEqual(search.selected.program.program_id, self.semantic.program.program_id)
        self.assertEqual(search.selected.program.filter_mode, 3)

    def test_proof_and_hidden_cases_pass(self) -> None:
        proof = verify_distinct_foundation_semantic(self.semantic)
        self.assertTrue(proof["passed"])
        self.assertEqual(sum(item["passed"] for item in proof["obligations"]), 18)
        self.assertEqual(sum(item["passed"] for item in proof["case_results"]), 13)
        self.assertFalse(proof["finite_sampling_used_as_proof"])

    def test_cardinality_has_falling_and_factorial_cases(self) -> None:
        executor = DistinctExecutor()
        falling = executor.execute(
            self.semantic.program, (opaque_symbols("B", 5), opaque_symbols("C", 3))
        )
        factorial = executor.execute(
            self.semantic.program, (opaque_symbols("B", 3), opaque_symbols("C", 3))
        )
        exhausted = executor.execute(
            self.semantic.program, (opaque_symbols("B", 2), opaque_symbols("C", 3))
        )
        self.assertEqual(len(falling.output), 60)
        self.assertEqual(len(factorial.output), 6)
        self.assertEqual(len(exhausted.output), 0)

    def test_memory_comparison_work_is_charged(self) -> None:
        result = DistinctExecutor().execute(
            self.semantic.program, (opaque_symbols("B", 4), opaque_symbols("C", 3))
        )
        self.assertGreater(result.equality_comparison_tokens, 0)
        self.assertGreaterEqual(result.primitive_execution_tokens, result.equality_comparison_tokens)

    def test_tampering_is_rejected(self) -> None:
        mutated = replace(
            self.semantic,
            program=replace(self.semantic.program, filter_mode=1),
        )
        self.assertFalse(verify_distinct_foundation_semantic(mutated)["passed"])

    def test_room_replays_previous_gap_and_next_gap(self) -> None:
        room = DistinctFrontierRoom(
            ROOT / "artifacts/foundation/success/distinct_frontier_semantics.jsonl"
        )
        self.assertEqual(len(room.records), 1)
        self.assertEqual(room.records[0]["semantic"]["semantic_id"], "XSEM-e27ac00be31ef317")
        self.assertEqual(self.report["resumed_from"]["missing_dependency"], "object_exclusion_memory")
        self.assertEqual(self.report["next_frontier"]["missing_dependency"], "order_canonicalization")


if __name__ == "__main__":
    unittest.main()
