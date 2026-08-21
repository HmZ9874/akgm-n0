from __future__ import annotations
import json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator import UniversalFormulaRoom
from akgm_n0.learner import ReflectiveExecutor,advanced_parametric_programs

class AdvancedParametricFrontierTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.discovery=json.loads((ROOT/"reports/data/advanced_parametric_ten_latest.json").read_text(encoding="utf-8"));cls.proof=json.loads((ROOT/"reports/data/advanced_parametric_proof_latest.json").read_text(encoding="utf-8"))
 def test_second_ten_are_exact_distinct_free_variable_programs(self):
  tasks=self.discovery["tasks"];self.assertEqual(len(tasks),10);self.assertTrue(all(g["passed"] for g in self.discovery["gates"]));self.assertEqual(len({tuple(t["candidate"]["program"]["words"]) for t in tasks}),10);self.assertTrue(all(all(x["passed"] for x in t["hidden_results"]) for t in tasks))
 def test_advanced_algorithms_execute_without_special_opcodes(self):
  p=advanced_parametric_programs();e=ReflectiveExecutor(maximum_steps=200000)
  cases={"affine":((2,3,4),14),"arithmetic_sum":((2,3,4),26),"rising":((3,4),360),"generalized_fibonacci":((2,3,5),21),"digit_length":((100,10),3),"floor_log":((100,10),2),"lcm":((12,18),36),"mod_power":((8,5,7),pow(8,5,7)),"geometric_sum":((3,4),121),"second_difference":((1,2,3,4),27)}
  for key,(inputs,expected) in cases.items():
   with self.subTest(key=key):self.assertEqual(e.execute(p[key][1],inputs).output_value,expected)
 def test_strict_room_replays_thirty_records_and_batch_has_twenty_new(self):
  room=UniversalFormulaRoom(ROOT/"artifacts/formula_rooms/parametric/proven_formulas.jsonl");self.assertGreaterEqual(len(room.records),30);self.assertGreaterEqual(len({r.theorem_kind for r in room.records}),30);self.assertEqual(self.proof["batch_newly_synthesized_count"],20);self.assertEqual(len(self.proof["batch_new_formulas"]),20);self.assertEqual(self.proof["proof_obligation_count"],self.proof["proof_obligation_passed_count"])
if __name__=="__main__":unittest.main()
