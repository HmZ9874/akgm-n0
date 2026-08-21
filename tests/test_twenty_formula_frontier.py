from __future__ import annotations

import sys
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    NumericTableObservation,
    TwentyFormulaFrontierSearch,
    anonymous_shape_programs,
    structural_logic_signature,
)


def recurrence(seeds, count):
    values = list(seeds)
    while len(values) < count:
        values.append(sum(values[-len(seeds):]))
    return tuple(values[:count])


def padovan(count):
    values = [1, 1, 1]
    while len(values) < count:
        values.append(values[-2] + values[-3])
    return tuple(values[:count])


def observation(index, rows, outputs):
    return NumericTableObservation.create(
        opaque_session_id=f"twenty-{index}", input_rows=rows, output_values=outputs,
        validity_mask=(True,) * len(rows), action_receipt="anonymous-twenty-frontier",
    )


class TwentyFormulaFrontierTests(unittest.TestCase):
    def test_active_stop_policy_requires_twenty_non_parameter_variants(self) -> None:
        policy = json.loads((PROJECT_ROOT / "configs" / "discovery_stop_policy.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["minimum_new_successful_formulas_per_batch"], 20)
        self.assertFalse(policy["allow_parameter_only_variants_to_count_as_new"])

    def test_twenty_shapes_have_distinct_non_parameter_logic_signatures(self) -> None:
        programs = anonymous_shape_programs()
        self.assertEqual(len(programs), 20)
        self.assertEqual(len({structural_logic_signature(program) for program in programs}), 20)

    def test_anonymous_behavior_selection_finds_all_twenty(self) -> None:
        unary = tuple((n,) for n in range(10))
        binary = ((0, 1), (1, 1), (2, 3), (3, 2), (7, 3), (8, 4), (11, 5), (20, 6), (25, 7), (31, 9))
        signed = tuple((n,) for n in (-9, -2, -1, 0, 1, 3, 8))
        lucas = [2, 1]
        pell = [0, 1]
        while len(lucas) < 10:
            lucas.append(lucas[-1] + lucas[-2])
            pell.append(2 * pell[-1] + pell[-2])
        tasks = (
            (unary, tuple(3**n for n in range(10))),
            (unary, tuple(2**n - 1 for n in range(10))),
            (unary, tuple(n**3 for n in range(10))),
            (unary, tuple(n*(n+1)*(2*n+1)//6 for n in range(10))),
            (unary, tuple(n*(n-1)*(n-2)*(n-3)*(n-4)//120 for n in range(10))),
            (unary, tuple(lucas)),
            (unary, tuple(pell)),
            (unary, padovan(10)),
            (unary, recurrence((0, 0, 0, 1), 10)),
            (unary, tuple(n % 3 for n in range(10))),
            (unary, tuple(n // 3 for n in range(10))),
            (unary, tuple(0 if n == 0 else len(_base3(n)) for n in range(10))),
            (binary, tuple(min(a, b) for a, b in binary)),
            (binary, tuple(abs(a-b) for a, b in binary)),
            (binary, tuple(a % b for a, b in binary)),
            (binary, tuple((a+b-1)//b for a, b in binary)),
            (binary, tuple(int(a % b == 0) for a, b in binary)),
            (binary, tuple(int(a == b) for a, b in binary)),
            (binary, tuple(int(a < b) for a, b in binary)),
            (signed, tuple((n > 0) - (n < 0) for (n,) in signed)),
        )
        search = TwentyFormulaFrontierSearch()
        winners = []
        for index, (rows, outputs) in enumerate(tasks):
            winner = search.search(observation(index, rows, outputs)).top_candidates[0]
            self.assertTrue(winner.exact, msg=f"shape task {index}")
            winners.append(winner)
        self.assertEqual(len({winner.program.words for winner in winners}), 20)


def _base3(value):
    digits = []
    while value:
        digits.append(value % 3)
        value //= 3
    return digits


if __name__ == "__main__":
    unittest.main()
