import unittest

from akgm_n0.evaluator.strict_counter_foundation_v10 import prove_counter_foundation
from akgm_n0.learner.strict_counter_foundation_v10 import (
    CounterExecutor,
    CounterProgram,
    TargetFreeCounterExplorer,
)


class StrictCounterFoundationV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discovery = TargetFreeCounterExplorer().search()
        cls.program = cls.discovery.selected.program
        cls.proof = prove_counter_foundation(cls.program)

    def test_target_free_search_finds_one_promotable_behavior(self):
        self.assertEqual(self.discovery.programs_generated, 4608)
        self.assertEqual(self.discovery.behavior_classes, 55)
        self.assertEqual(self.discovery.promotable_behavior_classes, 1)

    def test_selected_program_has_no_named_arithmetic_opcode(self):
        encoded = str(self.program.to_dict()).lower()
        for forbidden in ("multiply", "multiplication", "divide", "power"):
            self.assertNotIn(forbidden, encoded)

    def test_selected_behavior_replays_outside_probe_grid(self):
        executor = CounterExecutor()
        for left, right in ((0, 31), (1, 19), (5, 7), (11, 13), (29, 3)):
            self.assertEqual(executor.execute(self.program, (left, right)).output, left * right)

    def test_universal_invariant_is_accepted(self):
        self.assertTrue(self.proof.passed)
        self.assertEqual(self.proof.derived_normal_form, "x*y")
        self.assertTrue(all(item["passed"] for item in self.proof.obligations))

    def test_output_mutation_is_rejected(self):
        mutated = CounterProgram(
            self.program.outer_source,
            self.program.first_move,
            self.program.second_move,
            3 if self.program.output_register != 3 else 2,
        )
        self.assertFalse(prove_counter_foundation(mutated).passed)


if __name__ == "__main__":
    unittest.main()
