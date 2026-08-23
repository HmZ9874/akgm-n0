import unittest
from fractions import Fraction

from akgm_n0.evaluator.anonymous_field_construction_v53 import (
    replay_v53_report,
    run_v53_acceptance,
)
from akgm_n0.learner.anonymous_field_construction_v53 import (
    AnonymousFieldConstructorV53,
    AnonymousFieldRuntimeV53,
    NonzeroUnaryDomainErrorV53,
)
from akgm_n0.learner.directed_rational_construction_v21 import DirectedRuntimeV21, DirectedValueV21
from akgm_n0.learner.proof_driven_program_construction_v20 import AnonymousDerivedRuntimeV20


class AnonymousFieldConstructionV53Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v53_acceptance()

    def test_frozen_search_space_and_unique_behavior_class(self):
        construction = self.acceptance["construction"]
        self.assertEqual(construction["unary_programs_generated"], 64)
        self.assertEqual(construction["unary_behavior_classes"], 37)
        self.assertEqual(construction["three_input_programs_generated"], 1296)
        self.assertEqual(construction["three_input_passing_programs"], 4)
        self.assertEqual(construction["three_input_passing_behavior_classes"], 1)

    def test_selected_programs_were_anonymous(self):
        construction = self.acceptance["construction"]
        unary = construction["selected_nonzero_unary"]["policy"]
        solver = construction["selected_three_input"]
        self.assertIsNone(unary["human_operation_name"])
        self.assertIsNone(solver["human_operation_name"])
        self.assertFalse(solver["target_expression_given"])
        self.assertEqual(unary["numerator_source"], "source_denominator")
        self.assertEqual(unary["denominator_source"], "magnitude")
        self.assertEqual(solver["leaf_order"], ["b", "c", "a"])

    def test_all_universal_proofs_pass(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(proof["passed"] for proof in self.acceptance["proofs"].values()))
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))

    def test_nonzero_program_rejects_zero_class(self):
        construction = AnonymousFieldConstructorV53().construct()
        base = construction.dependency.base_construction
        directed = construction.dependency
        runtime = AnonymousFieldRuntimeV53(
            directed=DirectedRuntimeV21(
                AnonymousDerivedRuntimeV20(
                    base.operation_program, base.partition_report.selected.program
                )
            ),
            combine=directed.selected_combine.policy,
            additive_unary=directed.selected_inverse,
            interact=directed.selected_interact.policy,
        )
        with self.assertRaises(NonzeroUnaryDomainErrorV53):
            runtime.execute_nonzero_unary(
                construction.selected_nonzero_unary.policy,
                DirectedValueV21(9, 9, 7),
            )
        self.assertIsNotNone(AnonymousDerivedRuntimeV20(base.operation_program, base.partition_report.selected.program))

    def test_unseen_negative_fraction_replays(self):
        hidden = self.acceptance["proofs"]["general_first_degree_solver"]["hidden_replay"]
        self.assertTrue(all(item["passed"] for item in hidden))
        values = hidden[1]["output"]
        observed = Fraction(values["positive"] - values["negative"], values["denominator"])
        self.assertEqual(observed, Fraction(2, 3))

    def test_all_registered_mutations_have_counterexamples(self):
        mutations = self.acceptance["mutation_audits"]
        self.assertEqual(len(mutations), 23)
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in mutations))

    def test_report_is_replayable(self):
        report = {
            "observed_values": self.acceptance["observed_values"],
            "construction": self.acceptance["construction"],
        }
        self.assertTrue(replay_v53_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
