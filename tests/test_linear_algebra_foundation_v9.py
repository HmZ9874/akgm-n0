from __future__ import annotations
import json,tempfile,unittest
from fractions import Fraction
from pathlib import Path
from akgm_n0.evaluator.linear_algebra_foundation_v9 import replay_linear_algebra_foundation_v9
from akgm_n0.evaluator.linear_algebra_foundation_v9_room import LinearAlgebraFoundationV9Room
from akgm_n0.learner.linear_algebra_foundation_v9 import LinearAlgebraFoundationV9,_matrix
ROOT=Path(__file__).resolve().parents[1]
class LinearAlgebraFoundationV9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.persisted=json.loads((ROOT/"reports/data/linear_algebra_foundation_v9_latest.json").read_text(encoding="utf-8"));cls.report=cls.persisted["foundation"];cls.f=LinearAlgebraFoundationV9.from_dict(cls.report["foundation"])
    def test_levels_21_to_24_pass(self):self.assertTrue(self.report["passed"]);self.assertEqual(self.report["foundation_count_after"],24);self.assertEqual([x["foundation_level"] for x in self.report["proof"]["foundations"]],[21,22,23,24])
    def test_anonymous_search_spaces_are_nontrivial(self):self.assertFalse(self.report["names_or_target_formulas_visible_to_search"]);self.assertEqual(self.report["foundation"]["candidate_counts"],[32,200,384,25]);self.assertTrue(all(x>=1 for x in self.report["foundation"]["exact_counts"]))
    def test_composition_and_determinant_multiplicativity(self):
        a=_matrix((1,2,3,5));b=_matrix((7,-1,4,2));ab=self.f.composition.execute(a,b);self.assertEqual(self.f.determinant.execute(ab),self.f.determinant.execute(a)*self.f.determinant.execute(b))
    def test_inverse_is_both_sided(self):
        a=_matrix((2,1,3,2));inverse=self.f.inverse.execute(a,self.f.determinant);identity=_matrix((1,0,0,1));self.assertEqual(self.f.composition.execute(a,inverse),identity);self.assertEqual(self.f.composition.execute(inverse,a),identity)
    def test_characteristic_reduction_is_universal_structure(self):
        for values in ((1,2,3,4),(-2,5,7,1),(Fraction(1,2),Fraction(2,3),Fraction(-3,4),Fraction(5,6))):self.assertEqual(self.f.characteristic_reduction.execute(_matrix(values),self.f.composition,self.f.determinant),_matrix((0,0,0,0)))
    def test_replay_room_and_tamper_rejection(self):
        self.assertTrue(replay_linear_algebra_foundation_v9(self.report)["passed"]);forged=json.loads(json.dumps(self.report));forged["foundation"]["determinant"]["right_sign"]=1;self.assertFalse(replay_linear_algebra_foundation_v9(forged)["passed"])
        with tempfile.TemporaryDirectory() as directory:path=Path(directory)/"linear.jsonl";room=LinearAlgebraFoundationV9Room(path);room.record(self.report);self.assertEqual(len(LinearAlgebraFoundationV9Room(path).records),1)
if __name__=="__main__":unittest.main()
