import unittest
from akgm_n0.evaluator.hamiltonian_mechanics_v33 import replay_v33_report,run_v33_acceptance
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.a=run_v33_acceptance()
 def test_momentum(s):s.assertEqual(s.a["discovery"]["selected_momentum"]["opaque_program"],"MOMENTUM<M,V>")
 def test_flows(s):s.assertEqual(s.a["discovery"]["selected_q_flow"]["opaque_program"],"FLOW<KEEP;ONE*P/M>");s.assertEqual(s.a["discovery"]["selected_p_flow"]["opaque_program"],"FLOW<TURN;K*Q/ONE>")
 def test_hamiltonian(s):s.assertEqual(s.a["discovery"]["selected_hamiltonian"]["opaque_program"],"HAMILTON<P2/M,KEEP<K*Q2>>")
 def test_proofs(s):s.assertTrue(s.a["proofs"]["canonical"]["passed"] and s.a["proofs"]["symplectic"]["passed"])
 def test_mutations(s):s.assertTrue(all(i["rejected"] for i in s.a["mutation_audits"]))
 def test_progress(s):s.assertEqual(s.a["mechanics_capability_graph"]["verified_domains"],13)
 def test_replay(s):s.assertTrue(replay_v33_report({"observed_values":s.a["observed_values"],"discovery":s.a["discovery"]})["passed"])
if __name__=="__main__":unittest.main()
