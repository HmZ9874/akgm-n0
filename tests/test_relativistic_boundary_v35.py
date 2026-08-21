import unittest

from akgm_n0.evaluator.relativistic_boundary_v35 import replay_v35_report, run_v35_acceptance


class RelativisticBoundaryV35Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = run_v35_acceptance()

    def test_unique_program(self):
        self.assertEqual(
            self.acceptance["discovery"]["selected_program"]["opaque_program"],
            "FRAME<MERGE<Q1,Q2>;DEN:MERGE<ONE,SEM<Q1,Q2>/SEM<Q0,Q0>>>",
        )

    def test_invariant_role(self):
        self.assertEqual(self.acceptance["discovery"]["selected_invariant_role"], "Q0")

    def test_sealed_and_universal(self):
        self.assertTrue(self.acceptance["proofs"]["sealed_transfer"]["passed"])
        self.assertTrue(self.acceptance["proofs"]["universal"]["passed"])

    def test_low_speed_limit(self):
        self.assertTrue(self.acceptance["proofs"]["low_speed_limit"]["passed"])

    def test_mutations(self):
        self.assertTrue(all(i["rejected"] for i in self.acceptance["mutation_audits"]))

    def test_completion(self):
        graph = self.acceptance["mechanics_capability_graph"]
        self.assertEqual((graph["verified_domains"], graph["total_domains"]), (15, 15))
        self.assertTrue(graph["full_mechanics_claim_allowed"])

    def test_manifest(self):
        manifest = self.acceptance["completion_audit"]["evidence_manifest"]
        self.assertEqual(len(manifest), 15)
        self.assertTrue(all(all(i["evidence_dimensions"].values()) for i in manifest))

    def test_replay(self):
        report = {"observed_values": self.acceptance["observed_values"], "discovery": self.acceptance["discovery"]}
        self.assertTrue(replay_v35_report(report)["passed"])


if __name__ == "__main__":
    unittest.main()
