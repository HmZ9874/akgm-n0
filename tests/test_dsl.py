from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner.dsl import (
    EXECUTABLE_OPERATIONS,
    ExecutionContext,
    InvalidProgram,
    NumericExecutionError,
    ProgramExecutor,
    ProgramNode,
    add,
    argument,
    compose,
    parameter,
    read_offset,
    subtract,
)
from akgm_n0.contracts import load_primitive_manifest


class DslTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = ProgramExecutor()

    def test_program_executes_only_declared_numeric_operations(self) -> None:
        program = subtract(read_offset(1), read_offset(0))
        context = ExecutionContext.create([1, 4, 9, 16], index=1)
        self.assertEqual(self.executor.evaluate(program, context), 5.0)
        self.assertEqual(
            self.executor.evaluate_over_valid_indices(program, context),
            (3.0, 5.0, 7.0, None),
        )

    def test_parameter_slot_is_anonymous_and_explicit(self) -> None:
        program = add(read_offset(0), parameter(0))
        context = ExecutionContext.create([2, 3], index=0, parameters={0: 4.5})
        self.assertEqual(self.executor.evaluate(program, context), 6.5)

    def test_composition_is_compiled_before_execution(self) -> None:
        outer = add(argument(), parameter(0))
        program = compose(outer, read_offset(0))
        context = ExecutionContext.create([3], index=0, parameters={0: 2})
        self.assertNotIn("$argument", str(program.to_dict()))
        self.assertEqual(self.executor.evaluate(program, context), 5.0)

    def test_invalid_or_masked_read_is_rejected(self) -> None:
        program = read_offset(1)
        with self.assertRaises(NumericExecutionError):
            self.executor.evaluate(
                program,
                ExecutionContext.create([1, 2], index=0, validity_mask=[True, False]),
            )

    def test_undeclared_operation_is_rejected(self) -> None:
        with self.assertRaises(InvalidProgram):
            self.executor.evaluate(
                ProgramNode("unregistered_operation"),
                ExecutionContext.create([1], index=0),
            )

    def test_product_and_quotient_operations_are_not_in_the_runtime(self) -> None:
        context = ExecutionContext.create([2, 3], index=0)
        for operation in ("p_multiply", "p_divide"):
            with self.subTest(operation=operation), self.assertRaises(InvalidProgram):
                self.executor.evaluate(
                    ProgramNode(operation, args=(read_offset(0), read_offset(1))),
                    context,
                )

    def test_non_finite_parameter_is_rejected(self) -> None:
        with self.assertRaises(NumericExecutionError):
            self.executor.evaluate(
                parameter(0),
                ExecutionContext.create([1], index=0, parameters={0: math.inf}),
            )

    def test_resource_limits_are_enforced(self) -> None:
        program = read_offset(0)
        for _ in range(5):
            program = add(program, read_offset(0))
        executor = ProgramExecutor(maximum_depth=3)
        with self.assertRaises(InvalidProgram):
            executor.evaluate(program, ExecutionContext.create([1], index=0))

    def test_ast_round_trip(self) -> None:
        original = subtract(read_offset(1), parameter(2))
        restored = ProgramNode.from_dict(original.to_dict())
        self.assertEqual(original, restored)

    def test_runtime_operations_match_manifest(self) -> None:
        manifest = load_primitive_manifest()
        manifest_operations = {item["id"] for item in manifest["primitives"]}
        self.assertEqual(
            EXECUTABLE_OPERATIONS,
            manifest_operations - {"p_compose"},
        )


if __name__ == "__main__":
    unittest.main()
