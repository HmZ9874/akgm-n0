from __future__ import annotations
import json,tempfile,unittest
from fractions import Fraction
from pathlib import Path
from akgm_n0.evaluator.foundation_expansion_v8 import replay_foundation_expansion_v8
from akgm_n0.evaluator.foundation_expansion_v8_room import FoundationExpansionV8Room
from akgm_n0.learner.foundation_expansion_v8 import FoundationExpansionV8
ROOT=Path(__file__).resolve().parents[1]

class FoundationExpansionV8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.persisted=json.loads((ROOT/"reports/data/foundation_expansion_v8_latest.json").read_text(encoding="utf-8"));cls.report=cls.persisted["foundation"];cls.expansion=FoundationExpansionV8.from_dict(cls.report["expansion"])
    def test_four_new_contiguous_foundations_pass(self):
        self.assertTrue(self.report["passed"]);self.assertEqual(self.report["foundation_count_after"],20);self.assertEqual([x["foundation_level"] for x in self.report["proof"]["foundations"]],[17,18,19,20])
    def test_search_was_anonymous_and_nontrivial(self):
        self.assertFalse(self.report["names_or_target_formulas_visible_to_search"]);self.assertEqual(self.report["expansion"]["candidate_counts"],[128,6561,72,15]);self.assertTrue(all(x>=1 for x in self.report["expansion"]["exact_counts"]))
    def test_signed_rational_quotient_closes(self):
        self.assertEqual(self.expansion.quotient.execute((-8,3),(-4,7)),(14,3));self.assertEqual(self.expansion.quotient.execute((5,9),(10,3)),(1,6))
    def test_norm_composition_preserves_unit_circle(self):
        left=(Fraction(3,5),Fraction(4,5));right=(Fraction(5,13),Fraction(12,13));x,y=self.expansion.norm_composition.execute(left,right);self.assertEqual(x*x+y*y,1)
    def test_inverse_and_limit_have_explicit_failure_or_error_bounds(self):
        self.assertEqual(self.expansion.inverse_search.execute(3,81),(True,4));self.assertEqual(self.expansion.inverse_search.execute(3,20),(False,0));limit,current,bound=self.expansion.contraction_limit.execute(Fraction(1,2),Fraction(1),Fraction(0),10);self.assertEqual(limit,2);self.assertEqual(abs(current-limit),bound)
    def test_report_and_room_reject_tampering(self):
        self.assertTrue(replay_foundation_expansion_v8(self.report)["passed"]);forged=json.loads(json.dumps(self.report));forged["expansion"]["quotient"]["numerator_term"]=0;self.assertFalse(replay_foundation_expansion_v8(forged)["passed"])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"v8.jsonl";room=FoundationExpansionV8Room(path);room.record(self.report);self.assertEqual(len(FoundationExpansionV8Room(path).records),1)
if __name__=="__main__":unittest.main()
