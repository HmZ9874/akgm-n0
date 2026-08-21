import unittest
from fractions import Fraction

from akgm_n0.evaluator.directed_rational_construction_v21 import replay_v21_report, run_v21_acceptance
from akgm_n0.learner.directed_rational_construction_v21 import (
    DirectedRationalConstructorV21,
    DirectedRuntimeV21,
    DirectedValueV21,
)
from akgm_n0.learner.proof_driven_program_construction_v20 import AnonymousDerivedRuntimeV20


class DirectedRationalConstructionV21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v21_acceptance()

    def test_learner_values_contain_no_host_negative_numbers(self):
        self.assertTrue(all(all(value >= 0 for value in item.to_tuple()) for item in DirectedRationalConstructorV21.VALUES))

    def test_unique_direction_programs_are_selected(self):
        construction = self.acceptance["construction"]
        self.assertEqual(construction["combine_behavior_classes"], 16)
        self.assertEqual(construction["interact_behavior_classes"], 16)
        self.assertEqual(construction["selected_combine"]["policy"]["positive_mask"], [True, False, True, False])
        self.assertTrue(construction["selected_inverse"]["swap_counters"])
        self.assertEqual(construction["selected_interact"]["policy"]["positive_mask"], [True, False, False, True])

    def test_group_ring_and_equation_proofs_pass(self):
        proofs = self.acceptance["proofs"]
        self.assertTrue(proofs["equivalence"]["passed"])
        self.assertTrue(proofs["additive_group"]["passed"])
        self.assertTrue(proofs["commutative_ring"]["passed"])
        self.assertTrue(proofs["translation_equation"]["passed"])

    def test_translation_equations_replay(self):
        self.assertTrue(all(item["passed"] for item in self.acceptance["construction"]["equation_examples"]))

    def test_unseen_negative_result_is_executable_without_negative_counter(self):
        construction = DirectedRationalConstructorV21().construct()
        base = construction.base_construction
        runtime = DirectedRuntimeV21(AnonymousDerivedRuntimeV20(base.operation_program, base.partition_report.selected.program))
        left = DirectedValueV21(1, 0, 3)
        right = DirectedValueV21(0, 5, 7)
        output = runtime.execute_binary(construction.selected_combine.policy, left, right)
        self.assertTrue(all(value >= 0 for value in output.to_tuple()))
        self.assertEqual(Fraction(output.positive - output.negative, output.denominator), Fraction(1, 3) - Fraction(5, 7))

    def test_all_route_mutations_are_rejected(self):
        self.assertEqual(len(self.acceptance["mutation_audits"]), 9)
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in self.acceptance["mutation_audits"]))

    def test_full_acceptance_and_replay(self):
        self.assertTrue(self.acceptance["passed"])
        report = {"observed_values": self.acceptance["observed_values"], "construction": self.acceptance["construction"]}
        self.assertTrue(replay_v21_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
