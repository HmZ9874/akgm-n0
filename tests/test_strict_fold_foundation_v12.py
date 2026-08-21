import unittest

from akgm_n0.evaluator.strict_fold_foundation_v12 import prove_fold_foundation
from akgm_n0.learner.strict_fold_foundation_v12 import FoldExecutor, FoldProgram, TargetFreeFoldExplorer


class StrictFoldFoundationV12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discovery = TargetFreeFoldExplorer().search()
        cls.program = cls.discovery.selected.program
        cls.proof = prove_fold_foundation(cls.program)

    def test_search_discovers_one_role_orbit(self):
        self.assertEqual(self.discovery.programs_generated, 1200)
        self.assertEqual(self.discovery.behavior_classes, 103)
        self.assertEqual(self.discovery.promotable_behavior_classes, 2)

    def test_program_has_no_named_power_opcode(self):
        encoded = str(self.program.to_dict()).lower()
        for forbidden in ("power", "exponent", "pow"):
            self.assertNotIn(forbidden, encoded)

    def test_hidden_fold_behavior(self):
        executor = FoldExecutor(magnitude_limit=10**100)
        base_input = 1 - self.program.loop_input
        for base, count in ((0, 0), (2, 10), (3, 7), (11, 4)):
            inputs = (base, count) if base_input == 0 else (count, base)
            self.assertEqual(executor.execute(self.program, inputs).output, base**count)

    def test_universal_induction_passes(self):
        self.assertTrue(self.proof.passed)
        self.assertEqual(self.proof.derived_normal_form, "b^n")

    def test_seed_mutation_is_rejected(self):
        data = self.program.to_dict()
        data["seed_source"] = "zero"
        self.assertFalse(prove_fold_foundation(FoldProgram.from_dict(data)).passed)


if __name__ == "__main__":
    unittest.main()
