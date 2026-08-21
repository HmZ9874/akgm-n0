import unittest

from akgm_n0.evaluator.strict_partition_foundation_v11 import prove_partition_foundation
from akgm_n0.learner.strict_partition_foundation_v11 import (
    EventCounterExecutor,
    EventCounterProgram,
    TargetFreePartitionExplorer,
)


class StrictPartitionFoundationV11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discovery = TargetFreePartitionExplorer().search()
        cls.program = cls.discovery.selected.program
        cls.proof = prove_partition_foundation(cls.program)

    def test_search_has_one_promotable_behavior(self):
        self.assertEqual(self.discovery.programs_generated, 3072)
        self.assertEqual(self.discovery.behavior_classes, 6)
        self.assertEqual(self.discovery.promotable_behavior_classes, 1)

    def test_program_contains_no_named_division_opcode(self):
        encoded = str(self.program.to_dict()).lower()
        for forbidden in ("divide", "division", "quotient", "remainder", "modulo"):
            self.assertNotIn(forbidden, encoded)

    def test_hidden_behavior_has_unique_bounded_decomposition(self):
        executor = EventCounterExecutor()
        for stream, template in ((0, 3), (17, 5), (42, 8), (255, 16)):
            inputs = (stream, template) if self.program.stream_input == 0 else (template, stream)
            first, second = executor.execute(self.program, inputs).outputs
            self.assertEqual(first * template + second, stream)
            self.assertLess(second, template)

    def test_universal_proof_passes(self):
        self.assertTrue(self.proof.passed)
        self.assertEqual(self.proof.derived_normal_form, ("q=floor(n/d)", "r=n-d*q"))

    def test_policy_mutation_is_rejected(self):
        values = self.program.to_dict()
        values["policy_bits"]["boundary_clear_state_b"] = False
        mutated = EventCounterProgram.from_dict(values)
        self.assertFalse(prove_partition_foundation(mutated).passed)


if __name__ == "__main__":
    unittest.main()
