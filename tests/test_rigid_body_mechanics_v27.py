import unittest

from akgm_n0.evaluator.rigid_body_mechanics_v27 import replay_v27_report, run_v27_acceptance


class RigidBodyMechanicsV27Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v27_acceptance()

    def test_unique_inertia_aggregate_is_discovered(self):
        discovery = self.acceptance["discovery"]
        self.assertEqual(discovery["aggregate_candidates_generated"], 12)
        self.assertEqual(discovery["selected_aggregate"]["opaque_program"], "AGG<Q0,MERGE<SEM<Q1,Q1>,SEM<Q2,Q2>>>")

    def test_angular_response_and_quantity_transfer(self):
        self.assertEqual(self.acceptance["discovery"]["selected_angular_quantity"]["weight_route"], "AGG")
        proof = self.acceptance["proofs"]["rigid_response"]
        self.assertTrue(proof["passed"])
        self.assertTrue(all(item["passed"] for item in proof["hidden_replay"]))

    def test_parallel_axis_decomposition_is_proved(self):
        proof = self.acceptance["proofs"]["parallel_axis"]
        self.assertTrue(proof["passed"])
        self.assertFalse(proof["learner_was_given_theorem_name"])

    def test_angular_collision_dual_conservation_transfers(self):
        proof = self.acceptance["proofs"]["angular_collision"]
        self.assertTrue(proof["passed"])
        self.assertTrue(all(item["programs_passed"] and item["linear_passed"] and item["quadratic_passed"] for item in proof["hidden_replay"]))

    def test_mutations_are_rejected(self):
        mutations = self.acceptance["mutation_audits"]
        self.assertEqual(len(mutations), 4)
        self.assertTrue(all(item["rejected"] and item["counterexample"] for item in mutations))

    def test_completion_controller_refuses_false_complete_claim(self):
        graph = self.acceptance["mechanics_capability_graph"]
        self.assertEqual((graph["verified_domains"], graph["total_domains"]), (7, 15))
        self.assertFalse(graph["full_mechanics_claim_allowed"])
        self.assertTrue(graph["next_selected_gap"].startswith("M08"))

    def test_full_acceptance_and_replay(self):
        self.assertTrue(self.acceptance["passed"])
        report = {"observed_values": self.acceptance["observed_values"], "discovery": self.acceptance["discovery"]}
        self.assertTrue(replay_v27_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
