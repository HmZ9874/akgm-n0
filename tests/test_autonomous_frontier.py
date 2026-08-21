from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import AutonomousFrontierRoom, verify_recursive_foundation_semantic
from akgm_n0.learner import (
    AutonomousFrontierController,
    FrontierWorld,
    RecursiveExample,
    RecursiveExecutor,
    RecursiveExpansionSearch,
    RecursiveFoundationSemantic,
    opaque_symbols,
    recursive_word_observation,
)


ROOT = Path(__file__).resolve().parents[1]


class AutonomousFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/self_directed_frontier_latest.json").read_text(encoding="utf-8")
        )
        cls.semantic = RecursiveFoundationSemantic.from_dict(cls.report["discovery"]["semantic"])

    def test_controller_skips_known_blocks_missing_and_selects_novel_ready_world(self) -> None:
        worlds = (
            FrontierWorld("KNOWN", "nested_pairing", (), 10, 10, 1),
            FrontierWorld("READY", "recursive_state_expansion", ("nested_pairing",), 8, 10, 5),
            FrontierWorld("BLOCKED", "distinct_choice", ("missing_memory",), 20, 20, 1),
        )
        controller = AutonomousFrontierController()
        decisions = controller.rank(worlds, known_signatures=("nested_pairing",))
        selected = controller.select(decisions)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.world.world_id, "READY")
        self.assertEqual({item.world.world_id: item.status for item in decisions}, {
            "KNOWN": "already_explained",
            "READY": "ready",
            "BLOCKED": "dependency_blocked",
        })

    def test_recursive_search_has_one_exact_anonymous_program(self) -> None:
        examples = []
        for index, (base_count, control_count) in enumerate(((0, 0), (0, 1), (1, 5), (2, 3), (3, 2))):
            base = opaque_symbols(f"B{index}", base_count)
            control = opaque_symbols(f"C{index}", control_count)
            examples.append(RecursiveExample((base, control), recursive_word_observation(base, control)))
        search = RecursiveExpansionSearch().search("TEST-AUTO", examples)
        self.assertEqual(search.candidates_evaluated, 24)
        self.assertEqual(sum(item.exact for item in search.candidates), 1)
        self.assertEqual(search.selected.program.program_id, self.semantic.program.program_id)

    def test_proof_and_hidden_replays_pass(self) -> None:
        proof = verify_recursive_foundation_semantic(self.semantic)
        self.assertTrue(proof["passed"])
        self.assertEqual(sum(item["passed"] for item in proof["obligations"]), 15)
        self.assertEqual(sum(item["passed"] for item in proof["case_results"]), 12)
        self.assertFalse(proof["finite_sampling_used_as_proof"])

    def test_recursive_cardinalities_include_unit_and_growth(self) -> None:
        executor = RecursiveExecutor()
        unit = executor.execute(self.semantic.program, (opaque_symbols("B", 0), ()))
        grown = executor.execute(self.semantic.program, (opaque_symbols("B", 2), opaque_symbols("C", 5)))
        self.assertEqual(len(unit.output), 1)
        self.assertEqual(len(grown.output), 32)

    def test_tampering_is_rejected(self) -> None:
        mutated = replace(
            self.semantic,
            program=replace(self.semantic.program, controller_slot=0, base_slot=1),
        )
        self.assertFalse(verify_recursive_foundation_semantic(mutated)["passed"])

    def test_room_replays_and_report_records_self_selection(self) -> None:
        room = AutonomousFrontierRoom(
            ROOT / "artifacts/foundation/success/autonomous_frontier_semantics.jsonl"
        )
        self.assertEqual(len(room.records), 1)
        self.assertEqual(room.records[0]["semantic"]["semantic_id"], "ASEM-4b7c892702eaa68a")
        self.assertEqual(self.report["selected_world"]["world"]["world_id"], "WORLD-state-closure-27")
        self.assertFalse(self.report["discovery"]["name_given_to_controller_or_search"])


if __name__ == "__main__":
    unittest.main()
