import unittest
from fractions import Fraction

from akgm_n0.evaluator.strict_algebraic_closure_v14 import prove_congruence, prove_modular_fold, prove_modular_product, prove_rational_product
from akgm_n0.learner.strict_algebraic_closure_v14 import StrictAlgebraicClosureSearch
from akgm_n0.learner.strict_counter_foundation_v10 import TargetFreeCounterExplorer
from akgm_n0.learner.strict_fold_foundation_v12 import TargetFreeFoldExplorer
from akgm_n0.learner.strict_foundation_expansion_v13 import StrictFoundationExpander, StrictFoundationRuntime
from akgm_n0.learner.strict_partition_foundation_v11 import TargetFreePartitionExplorer


class StrictAlgebraicClosureV14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = StrictFoundationRuntime(TargetFreeCounterExplorer().search().selected.program, TargetFreePartitionExplorer().search().selected.program, TargetFreeFoldExplorer().search().selected.program)
        expansion = StrictFoundationExpander(cls.runtime)
        cls.searcher = StrictAlgebraicClosureSearch(cls.runtime, expansion.search_signed_product().selected.policy, expansion.search_integer_partition().selected.policy)
        cls.rational = cls.searcher.search_rational_product()
        cls.congruence = cls.searcher.search_congruence()
        cls.modular_product = cls.searcher.search_modular_product(cls.congruence.selected.policy)
        cls.modular_fold = cls.searcher.search_modular_fold(cls.congruence.selected.policy, cls.modular_product.selected.policy)

    def test_each_closure_has_one_passing_behavior(self):
        self.assertEqual(tuple(item.passing_behavior_classes for item in (self.rational, self.congruence, self.modular_product, self.modular_fold)), (1, 1, 1, 1))

    def test_rational_component_lift(self):
        policy = self.rational.selected.policy
        n, d = policy.execute(self.runtime, self.searcher.signed_product, (-2, 3), (4, 5))
        self.assertEqual(Fraction(n, d), Fraction(-8, 15))
        self.assertTrue(prove_rational_product(self.rational.selected).passed)

    def test_congruence_and_modular_product(self):
        congruence = self.congruence.selected.policy
        self.assertEqual(congruence.execute(self.runtime, self.searcher.partition, -17, 5), 3)
        product = self.modular_product.selected.policy.execute(self.runtime, self.searcher.signed_product, self.searcher.partition, congruence, -7, 11, 5)
        self.assertEqual(product, 3)
        self.assertTrue(prove_congruence(self.congruence.selected).passed)
        self.assertTrue(prove_modular_product(self.modular_product.selected).passed)

    def test_modular_fold(self):
        output = self.modular_fold.selected.policy.execute(self.runtime, self.searcher.signed_product, self.searcher.partition, self.congruence.selected.policy, self.modular_product.selected.policy, 7, 128, 13)
        self.assertEqual(output, pow(7, 128, 13))
        self.assertTrue(prove_modular_fold(self.modular_fold.selected).passed)


if __name__ == "__main__":
    unittest.main()
