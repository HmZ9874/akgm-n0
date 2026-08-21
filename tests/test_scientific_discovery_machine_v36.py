import unittest

from akgm_n0.evaluator.scientific_discovery_machine_v36 import replay_v36_report, run_v36_acceptance


class ScientificDiscoveryMachineV36Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_v36_acceptance()

    def test_active_unique_discovery(self):
        discovery = self.report["frontier_world"]["discovery"]
        self.assertGreaterEqual(discovery["initial_candidate_count"], 5000)
        self.assertGreaterEqual(len(discovery["active_experiments"]), 2)
        self.assertEqual(discovery["final_candidate_count"], 1)

    def test_opaque_program(self):
        self.assertEqual(
            self.report["frontier_world"]["discovery"]["selected_program"]["opaque_program"],
            "MERGE<DOUBLE<ONE>,Q0,TURN<Q1>,SEM<Q0,Q1>>",
        )

    def test_preregistered_future(self):
        self.assertTrue(self.report["frontier_world"]["preregistration"]["passed"])
        self.assertTrue(self.report["discovery_gates"]["commit_before_reveal"])

    def test_independent_replication(self):
        self.assertTrue(self.report["independent_replication"]["passed"])

    def test_mutations_rejected(self):
        self.assertEqual(len(self.report["mutation_audits"]), 12)
        self.assertTrue(all(item["rejected"] for item in self.report["mutation_audits"]))

    def test_novelty_labels(self):
        self.assertEqual(self.report["calibration_world"]["novelty"]["exact_matches"], ["KNOWN-ADD"])
        self.assertTrue(self.report["frontier_world"]["novelty"]["locally_unmatched"])

    def test_human_novelty_claim_blocked(self):
        self.assertFalse(self.report["claim_state"]["human_unknown_claim_allowed"])
        self.assertFalse(self.report["discovery_gates"]["real_world_observation"])

    def test_replay(self):
        self.assertTrue(replay_v36_report(self.report)["passed"])


if __name__ == "__main__":
    unittest.main()
