from __future__ import annotations
import json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator import UniversalFormulaRoom
from akgm_n0.learner import ReflectiveExecutor,ReflectiveProgram,strict_parametric_programs

class StrictParametricFrontierTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.discovery=json.loads((ROOT/"reports/data/strict_parametric_ten_latest.json").read_text(encoding="utf-8"));cls.proof=json.loads((ROOT/"reports/data/strict_parametric_twenty_latest.json").read_text(encoding="utf-8"))
 def test_ten_new_programs_are_exact_and_distinct(self):
  tasks=self.discovery["tasks"];self.assertEqual(len(tasks),10);self.assertTrue(all(g["passed"] for g in self.discovery["gates"]));self.assertEqual(len({tuple(t["candidate"]["program"]["words"]) for t in tasks}),10);self.assertTrue(all(all(x["passed"] for x in t["hidden_results"]) for t in tasks))
 def test_high_order_free_variable_programs_execute(self):
  p=strict_parametric_programs();e=ReflectiveExecutor(maximum_steps=100000)
  self.assertEqual(e.execute(p["mul"],(9,7)).output_value,63);self.assertEqual(e.execute(p["falling"],(8,4)).output_value,1680);self.assertEqual(e.execute(p["choose"],(8,4)).output_value,math.comb(8,4));self.assertEqual(e.execute(p["choose"],(4,5)).output_value,0)
 def test_first_twenty_remain_replayable_after_room_expansion(self):
  room=UniversalFormulaRoom(ROOT/"artifacts/formula_rooms/parametric/proven_formulas.jsonl");self.assertGreaterEqual(len(room.records),20);self.assertGreaterEqual(len({r.theorem_kind for r in room.records}),20);self.assertEqual(self.proof["proof_obligation_count"],self.proof["proof_obligation_passed_count"])
 def test_report_does_not_call_reclassification_new_discovery(self):
  self.assertEqual(self.proof["prior_parametric_count"],1);self.assertEqual(self.proof["historical_reclassified_count"],9);self.assertEqual(self.proof["newly_synthesized_count"],10);self.assertEqual(self.proof["strict_formula_count"],20)
if __name__=="__main__":unittest.main()
