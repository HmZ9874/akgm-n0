from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    CounterexampleGuidedReflectiveSearch,
    NumericTableObservation,
    ReflectiveExecutor,
    ReflectiveProgram,
    ReflectiveProgramSearch,
)
from akgm_n0.learner.metamachine_gen2 import (
    OP_ADD_CELL,
    OP_ADD_INPUT,
    OP_EMIT,
    OP_GROW,
    OP_HALT,
    OP_JUMP,
    OP_JUMP_IF_NEGATIVE,
    OP_JUMP_IF_ZERO,
    OP_LOAD_CELL,
    OP_SET,
    OP_STORE_CELL,
    OP_SUB_CELL,
)


class MetaMachineGen2Tests(unittest.TestCase):
    def test_unified_memory_can_modify_future_code(self) -> None:
        program = ReflectiveProgram(
            (
                OP_SET,
                7,
                OP_STORE_CELL,
                7,
                OP_JUMP,
                3,
                OP_SET,
                0,
                OP_EMIT,
                0,
                OP_HALT,
                0,
            )
        )
        result = ReflectiveExecutor().execute(program, ())
        self.assertEqual(result.output_value, 7)
        self.assertEqual(len(result.code_modifications), 1)
        self.assertEqual(result.code_modifications[0].address, 7)

    def test_program_can_grow_memory_and_use_new_cell(self) -> None:
        program = ReflectiveProgram(
            (
                OP_GROW,
                2,
                OP_SET,
                5,
                OP_STORE_CELL,
                12,
                OP_LOAD_CELL,
                12,
                OP_EMIT,
                0,
                OP_HALT,
                0,
            )
        )
        result = ReflectiveExecutor().execute(program, ())
        self.assertEqual(result.output_value, 5)
        self.assertEqual(len(result.memory_growth), 1)
        self.assertEqual(result.final_memory[12], 5)

    def test_one_generic_searcher_solves_anonymous_binary_relation(self) -> None:
        observation = NumericTableObservation.create(
            opaque_session_id="gen2-task-a",
            input_rows=((0, 0), (1, 2), (-2, 4), (5, -3)),
            output_values=(0, 3, 2, 2),
            validity_mask=(True, True, True, True),
            action_receipt="anonymous-word-task",
        )
        report = ReflectiveProgramSearch(top_k=20).search(observation)
        winner = report.top_candidates[0]
        self.assertTrue(winner.exact)
        self.assertIn(OP_ADD_INPUT, winner.program.words)

    def test_same_searcher_uses_counterexample_to_create_branch(self) -> None:
        search = ReflectiveProgramSearch(top_k=30)
        result = CounterexampleGuidedReflectiveSearch(
            search=search, maximum_rounds=4
        ).synthesize(
            opaque_task_id="gen2-task-b",
            input_rows=((0,), (2,), (7,), (-2,), (-5,)),
            output_values=(0, 2, 7, 2, 5),
            initial_case_indices=(0, 1, 2),
        )
        self.assertTrue(result.converged)
        self.assertGreaterEqual(len(result.rounds), 2)
        self.assertEqual(result.rounds[0].added_counterexample_index, 3)
        self.assertIn(OP_JUMP_IF_NEGATIVE, result.final_candidate.program.words)
        executor = ReflectiveExecutor()
        self.assertEqual(
            [executor.execute(result.final_candidate.program, (value,)).output_value for value in (-9, -1, 0, 4)],
            [9, 1, 0, 4],
        )

    def test_same_searcher_creates_two_distinct_dynamic_memory_loops(self) -> None:
        search = ReflectiveProgramSearch(top_k=30)
        repeated_input = NumericTableObservation.create(
            opaque_session_id="gen2-loop-c",
            input_rows=((2, 0), (2, 1), (2, 3), (3, 2), (4, 3), (5, 4)),
            output_values=(0, 2, 6, 6, 12, 20),
            validity_mask=(True,) * 6,
            action_receipt="anonymous-word-task",
        )
        changing_state = NumericTableObservation.create(
            opaque_session_id="gen2-loop-d",
            input_rows=((0,), (1,), (2,), (3,), (4,), (5,)),
            output_values=(0, 1, 3, 6, 10, 15),
            validity_mask=(True,) * 6,
            action_receipt="anonymous-word-task",
        )
        first = search.search(repeated_input).top_candidates[0]
        second = search.search(changing_state).top_candidates[0]
        self.assertTrue(first.exact)
        self.assertTrue(second.exact)
        self.assertIn(OP_GROW, first.program.words)
        self.assertIn(OP_JUMP, first.program.words)
        self.assertIn(OP_GROW, second.program.words)
        self.assertIn(OP_ADD_CELL, second.program.words)
        self.assertNotEqual(first.program.words, second.program.words)

    def test_same_searcher_finds_five_new_recurrent_behaviors(self) -> None:
        search = ReflectiveProgramSearch(
            top_k=30, executor=ReflectiveExecutor(maximum_steps=4096)
        )
        anonymous_tables = (
            (((0,), (1,), (2,), (3,), (4,), (5,)), (1, 2, 4, 8, 16, 32)),
            (((0,), (1,), (2,), (3,), (4,), (5,), (6,)), (0, 1, 1, 2, 3, 5, 8)),
            (((0,), (1,), (2,), (3,), (4,), (5,), (6,)), (1, 3, 7, 13, 21, 31, 43)),
            (((0,), (1,), (2,), (3,), (4,), (5,), (6,)), (0, 1, 0, 1, 0, 1, 0)),
            (((0,), (1,), (2,), (3,), (4,), (5,), (6,)), (1, 1, 2, 6, 24, 120, 720)),
        )
        winners = []
        for index, (rows, outputs) in enumerate(anonymous_tables):
            observation = NumericTableObservation.create(
                opaque_session_id=f"gen2-five-{index}",
                input_rows=rows,
                output_values=outputs,
                validity_mask=(True,) * len(rows),
                action_receipt="anonymous-word-task",
            )
            winner = search.search(observation).top_candidates[0]
            self.assertTrue(winner.exact, msg=f"anonymous table {index}")
            winners.append(winner)
        self.assertEqual(len({winner.program.words for winner in winners}), 5)
        self.assertTrue(all(OP_GROW in winner.program.words for winner in winners))
        self.assertTrue(all(OP_JUMP in winner.program.words for winner in winners))

    def test_same_searcher_finds_second_batch_of_five_control_behaviors(self) -> None:
        search = ReflectiveProgramSearch(
            top_k=30, executor=ReflectiveExecutor(maximum_steps=4096)
        )
        anonymous_tables = (
            (((0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,)), (0, 1, 1, 0, -1, -1, 0, 1)),
            (((0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,)), (0, 0, 0, 1, 4, 10, 20, 35)),
            (tuple((n,) for n in range(13)), tuple(n % 4 for n in range(13))),
            (((6, 4), (15, 10), (21, 14), (17, 5), (9, 3), (8, 12)), (2, 5, 7, 1, 3, 4)),
            (tuple((n,) for n in range(17)), tuple(int(n ** 0.5) for n in range(17))),
        )
        winners = []
        for index, (rows, outputs) in enumerate(anonymous_tables):
            observation = NumericTableObservation.create(
                opaque_session_id=f"gen2-five-second-{index}",
                input_rows=rows,
                output_values=outputs,
                validity_mask=(True,) * len(rows),
                action_receipt="anonymous-word-task",
            )
            winner = search.search(observation).top_candidates[0]
            self.assertTrue(winner.exact, msg=f"second-batch table {index}")
            winners.append(winner)
        self.assertEqual(len({winner.program.words for winner in winners}), 5)
        self.assertIn(OP_SUB_CELL, winners[0].program.words[::2])
        self.assertEqual(winners[1].program.words[1], 7)
        self.assertGreaterEqual(winners[2].program.words[::2].count(OP_JUMP), 2)
        self.assertIn(OP_JUMP_IF_ZERO, winners[3].program.words[::2])
        self.assertIn(OP_JUMP_IF_NEGATIVE, winners[4].program.words[::2])


if __name__ == "__main__":
    unittest.main()
