from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import (
    MetaAutonomyV3Room,
    run_meta_autonomy_benchmark,
    verify_meta_autonomy_report,
)
from akgm_n0.learner import (
    GeneralizedMistakeMemory,
    GrammarGenome,
    PolynomialInvariantMiner,
    compile_affine_program,
)


class MetaAutonomyV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_meta_autonomy_benchmark()

    def test_every_declared_dimension_is_at_least_eight(self) -> None:
        self.assertEqual(self.report["overall_score"], 8.0)
        self.assertTrue(all(value >= 8.0 for value in self.report["dimension_scores"].values()))
        self.assertTrue(self.report["passed"])

    def test_all_opaque_world_programs_pass_sealed_rows(self) -> None:
        self.assertEqual(len(self.report["sealed_results"]), 5)
        self.assertTrue(all(item["passed"] for item in self.report["sealed_results"]))
        self.assertTrue(all(not item["target_name_seen_by_learner"] for item in self.report["sealed_results"]))

    def test_grammar_grows_all_five_generic_resource_types(self) -> None:
        mutations = {
            mutation
            for item in self.report["autonomous_selections"]
            for mutation in item["mutations"]
        }
        self.assertEqual(mutations, {
            "grow_input_channel", "grow_state_cell", "grow_counter_fold",
            "grow_guarded_path", "grow_product_output",
        })
        self.assertNotEqual(self.report["initial_genome"], self.report["final_genome"])

    def test_failure_family_transfers_without_rejecting_correct_structure(self) -> None:
        memory = GeneralizedMistakeMemory(minimum_support=2)
        context = "shape:2>1"
        memory.observe(context, compile_affine_program((1, 0)), {"case": 1})
        memory.observe(context, compile_affine_program((2, 0), 1), {"case": 2})
        self.assertTrue(memory.rejects(context, compile_affine_program((-2, 0), 2)))
        self.assertFalse(memory.rejects(context, compile_affine_program((2, -1), 1)))

    def test_four_of_five_program_families_receive_exact_invariants(self) -> None:
        results = self.report["formal_proof_results"]
        self.assertEqual(sum(item["certificate_count"] > 0 for item in results), 4)
        self.assertTrue(all(item["passed"] for item in results))
        self.assertEqual(self.report["dimension_scores"]["formal_proof_autonomy"], 8.0)

    def test_independent_replay_rejects_tampering(self) -> None:
        self.assertTrue(verify_meta_autonomy_report(self.report)["passed"])
        forged = json.loads(json.dumps(self.report))
        forged["dimension_scores"]["formal_proof_autonomy"] = 10.0
        self.assertFalse(verify_meta_autonomy_report(forged)["passed"])

    def test_hash_chained_room_reloads_and_rejects_changed_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "room.jsonl"
            room = MetaAutonomyV3Room(path)
            room.record(self.report)
            self.assertEqual(len(MetaAutonomyV3Room(path).records), 1)
            event = json.loads(path.read_text(encoding="utf-8"))
            event["report"]["overall_score"] = 9.0
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                MetaAutonomyV3Room(path)

    def test_genome_mutations_are_structural_and_bounded(self) -> None:
        genome = GrammarGenome()
        self.assertEqual(genome.loop_depth, 0)
        self.assertEqual(genome.branch_slots, 0)


if __name__ == "__main__":
    unittest.main()
