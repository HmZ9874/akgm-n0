import unittest
from akgm_n0.evaluator.continuous_dynamics_v28 import replay_v28_report, run_v28_acceptance

class ContinuousDynamicsV28Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.acceptance = run_v28_acceptance()
    def test_unique_stencils(self):
        d = self.acceptance["discovery"]
        self.assertEqual(d["candidates_per_target"], 750)
        self.assertEqual(d["selected_target_0"]["opaque_program"], "STENCIL<TURN,ZERO,KEEP;H^1;S2>")
        self.assertEqual(d["selected_target_1"]["opaque_program"], "STENCIL<KEEP,TURN_DOUBLE,KEEP;H^2;S1>")
    def test_refinement_limit(self):
        self.assertEqual(self.acceptance["discovery"]["selected_refinement_order"], 2)
        self.assertTrue(self.acceptance["proofs"]["continuous_operators"]["passed"])
    def test_continuous_inertial_relation(self): self.assertTrue(self.acceptance["proofs"]["continuous_inertial_relation"]["passed"])
    def test_mutations(self): self.assertTrue(all(i["rejected"] and i["counterexample"] for i in self.acceptance["mutation_audits"]))
    def test_progress(self):
        g = self.acceptance["mechanics_capability_graph"]
        self.assertEqual((g["verified_domains"], g["total_domains"]), (8, 15)); self.assertTrue(g["next_selected_gap"].startswith("M09"))
    def test_replay(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertTrue(replay_v28_report({"observed_values": self.acceptance["observed_values"], "discovery": self.acceptance["discovery"]})["passed"])
if __name__ == "__main__": unittest.main()
