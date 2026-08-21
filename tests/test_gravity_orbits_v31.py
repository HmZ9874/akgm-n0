import unittest
from akgm_n0.evaluator.gravity_orbits_v31 import replay_v31_report,run_v31_acceptance
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.a=run_v31_acceptance()
 def test_field(s):s.assertEqual(s.a["discovery"]["selected_field"]["opaque_program"],"FIELD<TURN;SEM<Q0,R>;Q3^3>")
 def test_energy(s):s.assertEqual(s.a["discovery"]["selected_energy"]["opaque_program"],"ENERGY<MET<V,V>,TURN_DOUBLE<Q0/Q3^1>>")
 def test_proof(s):s.assertTrue(s.a["proofs"]["gravity_orbits"]["passed"])
 def test_classification(s):s.assertTrue(s.a["proofs"]["orbit_classification"]["passed"])
 def test_mutations(s):s.assertTrue(all(i["rejected"] for i in s.a["mutation_audits"]))
 def test_progress(s):s.assertEqual(s.a["mechanics_capability_graph"]["verified_domains"],11)
 def test_replay(s):s.assertTrue(replay_v31_report({"observed_values":s.a["observed_values"],"discovery":s.a["discovery"]})["passed"])
if __name__=="__main__":unittest.main()
