import unittest

from akgm_n0.evaluator.cold_start_semantics_v16 import (
    IndependentSemanticVerifierV16,
    anonymous_primitive_workloads,
    run_v16_acceptance,
)
from akgm_n0.learner.cold_start_semantics_v16 import (
    BASE_OPS,
    ColdStartSemanticResearcherV16,
    RuntimeInstruction,
    SelfExtendingCounterVM,
)


class ColdStartSemanticsV16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v16_acceptance(trials=20)

    def test_registry_really_starts_empty(self):
        researcher = ColdStartSemanticResearcherV16()
        self.assertEqual(researcher.vm.operators, ())
        self.assertEqual(len(BASE_OPS), 8)

    def test_discovery_uses_only_primitive_anonymous_workloads(self):
        workloads = anonymous_primitive_workloads(1234, phase_nonce="test-visible", workloads_per_family=12)
        discovery = ColdStartSemanticResearcherV16().discover(workloads, maximum_operators=6)
        self.assertEqual(discovery.manifest["initial_success_program_count"], 0)
        self.assertEqual(discovery.manifest["imported_program_count"], 0)
        self.assertEqual(discovery.manifest["target_formula_count"], 0)
        self.assertGreaterEqual(len(discovery.operators), 5)

    def test_installed_opcode_dispatches_without_pre_expansion(self):
        workloads = anonymous_primitive_workloads(4321, phase_nonce="dispatch-test", workloads_per_family=12)
        discovery = ColdStartSemanticResearcherV16().discover(workloads, maximum_operators=6)
        vm = SelfExtendingCounterVM()
        for definition in discovery.operators:
            vm.install_operator(definition)
        operator = discovery.operators[0]
        state = tuple(3 for _ in range(max(2, operator.arity)))
        _, dispatches, primitive_effects = vm.apply_sequence(
            (RuntimeInstruction(operator.operator_id, tuple(range(operator.arity))),), state,
        )
        self.assertGreater(dispatches, 0)
        self.assertGreater(primitive_effects, 0)

    def test_every_operator_has_an_independent_certificate(self):
        trial = self.acceptance["trials"][0]
        self.assertTrue(all(item["passed"] for item in trial["holdout"]["operator_verification"]))
        self.assertTrue(all(item["certificate_digest_matches"] for item in trial["holdout"]["operator_verification"]))

    def test_twenty_cold_starts_meet_transfer_and_compression_gates(self):
        aggregate = self.acceptance["aggregate"]
        self.assertEqual(self.acceptance["trial_count"], 20)
        self.assertGreaterEqual(aggregate["minimum_operators_per_trial"], 5)
        self.assertGreaterEqual(aggregate["minimum_generation_depth"], 2)
        self.assertGreaterEqual(aggregate["mean_holdout_token_reduction"], 0.30)
        self.assertEqual(aggregate["exact_holdout_replays"], aggregate["holdout_workloads"])
        self.assertTrue(all(
            all(item["family_support"] >= 3 for item in trial["holdout"]["operator_usage"])
            for trial in self.acceptance["trials"]
        ))

    def test_full_strict_acceptance(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(all(item["passed"] for item in self.acceptance["proof_obligations"]))
        self.assertEqual(self.acceptance["aggregate"]["mutations_rejected"], 20)
        self.assertEqual(self.acceptance["classification"], "verified_cold_start_runtime_semantic_abstraction")


if __name__ == "__main__":
    unittest.main()

