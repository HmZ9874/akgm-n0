import unittest
from fractions import Fraction

from akgm_n0.evaluator.strict_foundation_expansion_v13 import (
    prove_integer_partition,
    prove_rational_integer_power,
    prove_signed_product,
)
from akgm_n0.learner.strict_counter_foundation_v10 import TargetFreeCounterExplorer
from akgm_n0.learner.strict_fold_foundation_v12 import TargetFreeFoldExplorer
from akgm_n0.learner.strict_foundation_expansion_v13 import StrictFoundationExpander, StrictFoundationRuntime
from akgm_n0.learner.strict_partition_foundation_v11 import TargetFreePartitionExplorer


class StrictFoundationExpansionV13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = StrictFoundationRuntime(
            TargetFreeCounterExplorer().search().selected.program,
            TargetFreePartitionExplorer().search().selected.program,
            TargetFreeFoldExplorer().search().selected.program,
        )
        expander = StrictFoundationExpander(cls.runtime)
        cls.product = expander.search_signed_product()
        cls.partition = expander.search_integer_partition()
        cls.power = expander.search_rational_integer_power()

    def test_each_family_has_one_passing_behavior(self):
        self.assertEqual((self.product.passing_behavior_classes, self.partition.passing_behavior_classes, self.power.passing_behavior_classes), (1, 1, 1))

    def test_signed_product_expansion(self):
        policy = self.product.selected.policy
        self.assertEqual(policy.execute(self.runtime, -37, -19), 703)
        self.assertTrue(prove_signed_product(self.runtime, self.product.selected).passed)

    def test_integer_partition_expansion(self):
        policy = self.partition.selected.policy
        q, r = policy.execute(self.runtime, -101, 9)
        self.assertEqual(9 * q + r, -101)
        self.assertLess(r, 9)
        self.assertTrue(prove_integer_partition(self.runtime, self.partition.selected).passed)

    def test_rational_integer_power_expansion(self):
        policy = self.power.selected.policy
        numerator, denominator = policy.execute(self.runtime, -3, 2, -5)
        self.assertEqual(Fraction(numerator, denominator), Fraction(-3, 2) ** -5)
        self.assertTrue(prove_rational_integer_power(self.runtime, self.power.selected).passed)

    def test_expansions_are_not_counted_as_new_foundations(self):
        self.assertEqual({self.product.selected.family, self.partition.selected.family, self.power.selected.family}, {"signed_product", "integer_partition", "rational_integer_power"})


if __name__ == "__main__":
    unittest.main()
