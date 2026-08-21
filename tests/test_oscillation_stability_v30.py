import unittest
from akgm_n0.evaluator.oscillation_stability_v30 import replay_v30_report,run_v30_acceptance
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.a=run_v30_acceptance()
 def test_program(s):s.assertEqual(s.a["discovery"]["selected_response"]["opaque_program"],"RESTORE<TURN;NUM:SEM<K,X>;DEN:M>")
 def test_invariant(s):s.assertEqual(s.a["discovery"]["selected_invariant"]["opaque_program"],"MERGE<SEM<q0,SEM<q3,q3>>,SEM<q1,SEM<q2,q2>>>")
 def test_proof(s):s.assertTrue(s.a["proofs"]["oscillation"]["passed"])
 def test_stability(s):s.assertTrue(s.a["proofs"]["stability"]["passed"])
 def test_mutations(s):s.assertTrue(all(i["rejected"] for i in s.a["mutation_audits"]))
 def test_progress(s):s.assertEqual(s.a["mechanics_capability_graph"]["verified_domains"],10)
 def test_replay(s):s.assertTrue(replay_v30_report({"observed_values":s.a["observed_values"],"discovery":s.a["discovery"]})["passed"])
if __name__=="__main__":unittest.main()
