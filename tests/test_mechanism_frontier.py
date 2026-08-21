from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import MechanismFrontierSearch, NumericTableObservation, ReflectiveExecutor
from akgm_n0.learner.metamachine_gen2 import OP_STORE_CELL


def observation(task_id, rows, outputs):
    return NumericTableObservation.create(
        opaque_session_id=task_id,
        input_rows=rows,
        output_values=outputs,
        validity_mask=(True,) * len(rows),
        action_receipt="anonymous-mechanism-frontier",
    )


class MechanismFrontierTests(unittest.TestCase):
    def test_same_anonymous_search_finds_five_new_mechanisms(self) -> None:
        search = MechanismFrontierSearch(top_k=20)
        tribonacci = (0, 0, 1, 1, 2, 4, 7, 13, 24, 44)
        tasks = (
            (tuple((n,) for n in range(10)), tuple(n * n for n in range(10))),
            (tuple((n,) for n in range(10)), tuple(n * (n-1) * (n-2) * (n-3) // 24 for n in range(10))),
            (tuple((n,) for n in range(10)), tribonacci),
            (tuple((n,) for n in range(17)), tuple(0 if n == 0 else n.bit_length() for n in range(17))),
            (((0, 1), (1, 1), (5, 2), (8, 3), (14, 4), (25, 6), (37, 5)), (0, 1, 2, 2, 3, 4, 7)),
        )
        winners = []
        for index, (rows, outputs) in enumerate(tasks):
            winner = search.search(observation(f"frontier-{index}", rows, outputs)).top_candidates[0]
            self.assertTrue(winner.exact, msg=f"task {index}")
            winners.append(winner)
        self.assertEqual(len({winner.program.words for winner in winners}), 5)
        self.assertEqual(winners[0].program.words[1], 2)
        self.assertIn(17, winners[0].program.words[1::2])
        self.assertEqual(winners[1].program.words[1], 9)
        self.assertEqual(winners[2].program.words[1], 7)
        self.assertEqual(winners[3].program.words[1], 2)
        self.assertEqual(winners[4].program.words[1], 2)
        execution = ReflectiveExecutor(maximum_steps=4096).execute(winners[0].program, (8,))
        self.assertTrue(any(item.address == 17 for item in execution.code_modifications))


if __name__ == "__main__":
    unittest.main()
