"""Regression tests for truthful operation-family reporting."""

import unittest

from scripts.run_operation_family_experiment import render_relation_formula


class OperationFamilyReportTests(unittest.TestCase):
    def test_render_relation_formula_preserves_subtraction(self) -> None:
        definition = {
            "op": "r_subtract",
            "args": [{"op": "r_value"}, {"op": "r_value"}],
        }

        self.assertEqual(render_relation_formula(definition), "(x - x)")

    def test_render_relation_formula_preserves_nested_addition(self) -> None:
        definition = {
            "op": "r_add",
            "args": [
                {"op": "r_value"},
                {
                    "op": "r_subtract",
                    "args": [{"op": "r_value"}, {"op": "r_value"}],
                },
            ],
        }

        self.assertEqual(render_relation_formula(definition), "(x + (x - x))")

    def test_render_relation_formula_preserves_evidence_constant(self) -> None:
        definition = {"op": "r_constant", "constant": 1.0}

        self.assertEqual(render_relation_formula(definition), "1.0")


if __name__ == "__main__":
    unittest.main()
