from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenSequenceEnvironment, SequenceWorldSpec
from akgm_n0.learner import (
    CrossTaskConceptMiner,
    ExecutionContext,
    NextValueProgramSearch,
    ProgramExecutor,
    library_call,
)
from akgm_n0.learner.dsl import InvalidProgram


SECRET = b"concept-test-secret"


def make_observation(a: float, b: float, c: float, seed: int):
    spec = SequenceWorldSpec("polynomial2", (a, b, c), 14)
    return HiddenSequenceEnvironment(spec, seed=seed, secret=SECRET).observe(14)


def select_exact(report):
    exact = [
        candidate
        for candidate in report.top_candidates
        if candidate.train_mse <= 1e-12 and candidate.validation_mse <= 1e-12
    ]
    if not exact:
        raise AssertionError("expected an exact candidate in the registered test task")
    return min(exact, key=lambda item: (item.program_nodes, item.candidate_id))


class ConceptTests(unittest.TestCase):
    def build_library(self):
        task_programs = {}
        parameters = [(1, 0, 1), (2, 3, -4), (-1, 5, 8), (3, -2, 6)]
        for index, (a, b, c) in enumerate(parameters):
            report = NextValueProgramSearch(
                maximum_nodes=7,
                top_k=30,
                complexity_weight=1e-6,
            ).search(make_observation(a, b, c, index))
            task_programs[f"TASK-{index:02d}"] = select_exact(report).program
        miner = CrossTaskConceptMiner(minimum_support_tasks=3)
        candidates = miner.mine(task_programs)
        self.assertTrue(candidates)
        return miner.promote(candidates), candidates[0]

    def test_cross_task_miner_promotes_anonymous_parameter_free_subprogram(self) -> None:
        library, candidate = self.build_library()
        self.assertEqual(len(library.entries), 1)
        self.assertEqual(len(candidate.support_task_ids), 4)
        self.assertGreater(candidate.description_gain, 0)
        self.assertIsNone(candidate.to_dict()["human_interpretation"])

    def test_library_call_executes_definition(self) -> None:
        library, candidate = self.build_library()
        executor = ProgramExecutor(library=library.definitions())
        context = ExecutionContext.create([1, 4, 9], index=1)
        direct = executor.evaluate(candidate.definition, context)
        through_library = executor.evaluate(library_call(candidate.concept_id), context)
        self.assertEqual(direct, through_library)

    def test_library_reduces_transfer_search_space_and_program_size(self) -> None:
        library, _ = self.build_library()
        held_out = make_observation(4, 7, -10, 99)
        without_library = NextValueProgramSearch(
            maximum_nodes=7,
            top_k=30,
            complexity_weight=1e-6,
        ).search(held_out)
        with_library = NextValueProgramSearch(
            maximum_nodes=5,
            top_k=30,
            complexity_weight=1e-6,
            concept_library=library.definitions(),
        ).search(held_out)
        baseline = select_exact(without_library)
        transfer = select_exact(with_library)
        self.assertLess(with_library.programs_generated, without_library.programs_generated)
        self.assertLess(transfer.program_nodes, baseline.program_nodes)
        self.assertGreater(
            1 - with_library.programs_generated / without_library.programs_generated,
            0.30,
        )

    def test_cyclic_library_is_rejected(self) -> None:
        with self.assertRaises(InvalidProgram):
            ProgramExecutor(library={"C-cycle": library_call("C-cycle")})


if __name__ == "__main__":
    unittest.main()

