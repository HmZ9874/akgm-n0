import unittest
from akgm_n0.evaluator.lagrangian_mechanics_v32 import replay_v32_report,run_v32_acceptance
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.a=run_v32_acceptance()
 def test_action(s):s.assertEqual(s.a["discovery"]["selected_action"]["opaque_program"],"ACTION<KW:M;PW:K;P:TURN;H^2>")
 def test_proof(s):s.assertTrue(s.a["proofs"]["variational"]["passed"])
 def test_sealed(s):s.assertTrue(all(i["passed"] for i in s.a["proofs"]["variational"]["hidden_replay"]))
 def test_mutations(s):s.assertTrue(all(i["rejected"] for i in s.a["mutation_audits"]))
 def test_progress(s):s.assertEqual(s.a["mechanics_capability_graph"]["verified_domains"],12)
 def test_replay(s):s.assertTrue(replay_v32_report({"observed_values":s.a["observed_values"],"discovery":s.a["discovery"]})["passed"])
if __name__=="__main__":unittest.main()
