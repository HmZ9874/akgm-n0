import unittest
from akgm_n0.evaluator.constraint_mechanics_v29 import replay_v29_report,run_v29_acceptance
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c): c.a=run_v29_acceptance()
 def test_programs(s):
  d=s.a["discovery"]; s.assertEqual(d["selected_metric"]["opaque_program"],"MET<KEEP,ZERO,ZERO,KEEP>"); s.assertEqual(d["selected_tangent"]["opaque_program"],"TANGENT<TURN<q1>,KEEP<q0>>"); s.assertEqual(d["selected_projection"]["opaque_program"],"PROJECT<TURN;DEN:MET<R,R>>")
 def test_proof(s): s.assertTrue(s.a["proofs"]["constraint"]["passed"])
 def test_reconstruction(s): s.assertTrue(all(i["reconstruction_passed"] for i in s.a["proofs"]["constraint"]["hidden_replay"]))
 def test_mutations(s): s.assertTrue(all(i["rejected"] for i in s.a["mutation_audits"]))
 def test_progress(s): s.assertEqual(s.a["mechanics_capability_graph"]["verified_domains"],9)
 def test_replay(s): s.assertTrue(replay_v29_report({"observed_values":s.a["observed_values"],"discovery":s.a["discovery"]})["passed"])
if __name__=="__main__": unittest.main()
