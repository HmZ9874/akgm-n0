from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from akgm_n0.evaluator.meta_autonomy_v4_benchmark import (
    run_deep_research_benchmark,
    verify_deep_research_report,
)
from akgm_n0.evaluator.meta_autonomy_v4_room import MetaAutonomyV4Room
from akgm_n0.learner.meta_autonomy_v3 import (
    AdaptiveGrammarSynthesizer,
    AnonymousWorld,
    GrammarGenome,
)
from akgm_n0.learner.meta_autonomy_v4 import AutonomousProofPortfolio


class MetaAutonomyV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_deep_research_benchmark()

    def test_expanded_benchmark_passes_every_dimension(self) -> None:
        self.assertTrue(self.report["passed"])
        self.assertGreaterEqual(self.report["overall_score"], 9.9)
        self.assertTrue(all(value >= 9.9 for value in self.report["dimension_scores"].values()))

    def test_eleven_worlds_pass_sealed_replay(self) -> None:
        self.assertEqual(len(self.report["sealed_results"]), 11)
        self.assertTrue(all(item["passed"] for item in self.report["sealed_results"]))

    def test_every_loop_receives_a_replayable_proof(self) -> None:
        self.assertEqual(len(self.report["proof_results"]), 8)
        self.assertTrue(all(item["passed"] and item["proofs"] for item in self.report["proof_results"]))

    def test_counter_interaction_is_discovered_without_factorial_primitive(self) -> None:
        world = AnonymousWorld.create("opaque", tuple((i,) for i in range(6)), (1, 1, 2, 6, 24, 120))
        result = AdaptiveGrammarSynthesizer(maximum_rounds=10).solve(world, GrammarGenome())
        self.assertTrue(result.converged)
        self.assertIn("grow_counter_interaction", [item.mutation for item in result.rounds])
        self.assertEqual(result.final_candidate.program.execute((7,)), (5040,))
        self.assertIn("counter_product_induction", {item.proof_domain for item in AutonomousProofPortfolio().prove(result.final_candidate.program)})

    def test_library_compression_materially_reduces_search(self) -> None:
        library = self.report["library_learning"]
        self.assertEqual(library["macro_candidates"], 3)
        self.assertEqual(library["primitive_baseline_candidates"], 4887)
        self.assertGreater(library["candidate_reduction_fraction"], 0.99)
        self.assertTrue(library["transfer_sealed"]["passed"])

    def test_tampering_fails_digest_and_replay(self) -> None:
        self.assertTrue(verify_deep_research_report(self.report)["passed"])
        forged = json.loads(json.dumps(self.report))
        forged["library_learning"]["macro_candidates"] = 1
        self.assertFalse(verify_deep_research_report(forged)["passed"])

    def test_success_room_is_hash_chained_and_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "room.jsonl"
            MetaAutonomyV4Room(path).record(self.report)
            self.assertEqual(len(MetaAutonomyV4Room(path).records), 1)


if __name__ == "__main__":
    unittest.main()
