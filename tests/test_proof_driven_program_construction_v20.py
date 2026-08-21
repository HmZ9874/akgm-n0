import unittest

from akgm_n0.evaluator.proof_driven_program_construction_v20 import replay_v20_report, run_v20_acceptance
from akgm_n0.learner.proof_driven_program_construction_v20 import (
    AnonymousDerivedRuntimeV20,
    ProofDrivenProgramConstructorV20,
)


class ProofDrivenProgramConstructionV20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v20_acceptance()

    def test_partition_program_is_target_free_and_unique(self):
        construction = self.acceptance["construction"]
        self.assertEqual(construction["partition_programs_generated"], 3072)
        self.assertEqual(construction["partition_promotable_classes"], 1)
        self.assertTrue(self.acceptance["proofs"]["partition"]["passed"])

    def test_equation_solver_distinguishes_exact_and_nonexact_cases(self):
        examples = self.acceptance["construction"]["equation_examples"]
        by_input = {(item["coefficient"], item["target"]): item for item in examples}
        self.assertTrue(by_input[3, 21]["solved"])
        self.assertEqual(by_input[3, 21]["candidate"], 7)
        self.assertFalse(by_input[4, 18]["solved"])
        self.assertEqual(by_input[4, 18]["residual"], 2)

    def test_pair_search_promotes_two_distinct_programs(self):
        construction = self.acceptance["construction"]
        self.assertGreaterEqual(construction["pair_programs_generated"], 1000)
        self.assertGreaterEqual(construction["pair_behavior_classes"], 500)
        self.assertEqual(len(construction["promoted_pair_operations"]), 2)
        identities = {tuple(item["law_profile"]["identity_pair"]) for item in construction["promoted_pair_operations"]}
        self.assertEqual(identities, {(0, 1), (1, 1)})

    def test_pair_programs_are_representation_independent_and_proven(self):
        self.assertTrue(self.acceptance["proofs"]["pair_equivalence"]["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proofs"]["pair_operations"]))
        self.assertTrue(all(item["law_profile"]["representation_invariant"] for item in self.acceptance["construction"]["promoted_pair_operations"]))

    def test_mutated_shortcuts_are_rejected(self):
        self.assertEqual(len(self.acceptance["mutation_audits"]), 2)
        self.assertTrue(all(item["rejected"] for item in self.acceptance["mutation_audits"]))

    def test_runtime_solves_unseen_equation(self):
        construction = ProofDrivenProgramConstructorV20().construct()
        runtime = AnonymousDerivedRuntimeV20(construction.operation_program, construction.partition_report.selected.program)
        result = runtime.solve_right(37, 1369)
        self.assertTrue(result.solved)
        self.assertEqual(result.candidate, 37)
        self.assertFalse(runtime.solve_right(37, 1370).solved)

    def test_full_acceptance_and_replay(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))
        report = {"observed_values": self.acceptance["observed_values"], "construction": self.acceptance["construction"]}
        self.assertTrue(replay_v20_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
