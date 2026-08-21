import unittest
from akgm_n0.evaluator.continuum_mechanics_v34 import replay_v34_report,run_v34_acceptance
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.a=run_v34_acceptance()
 def test_fluxes(s):s.assertEqual(s.a["discovery"]["selected_mass_flux"]["opaque_program"],"SEM<RHO,U>");s.assertEqual(s.a["discovery"]["selected_momentum_flux"]["opaque_program"],"MERGE<SEM<RHO,U,U>,P>")
 def test_balance(s):s.assertEqual(s.a["discovery"]["selected_balance"]["opaque_program"],"BALANCE<L:KEEP;R:TURN;DT^1;DX:DIV>")
 def test_proofs(s):s.assertTrue(s.a["proofs"]["continuum"]["passed"] and s.a["proofs"]["refinement"]["passed"])
 def test_mutations(s):s.assertTrue(all(i["rejected"] for i in s.a["mutation_audits"]))
 def test_progress(s):s.assertEqual(s.a["mechanics_capability_graph"]["verified_domains"],14)
 def test_replay(s):s.assertTrue(replay_v34_report({"observed_values":s.a["observed_values"],"discovery":s.a["discovery"]})["passed"])
if __name__=="__main__":unittest.main()
