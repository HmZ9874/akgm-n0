from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenSequenceEnvironment, SequenceWorldSpec
from akgm_n0.learner.search import (
    NextValueProgramSearch,
    ProgramEnumerator,
    iter_read_offsets,
    program_key,
)


def affine_observation():
    environment = HiddenSequenceEnvironment(
        SequenceWorldSpec("affine", (2.0, 3.0), 12),
        seed=104729,
        secret=b"search-test-secret",
    )
    return environment.observe(10)


class ProgramEnumeratorTests(unittest.TestCase):
    def test_enumeration_is_deterministic_and_unique(self) -> None:
        enumerator = ProgramEnumerator(readable_offsets=(-1, 0))
        first = enumerator.enumerate(5)
        second = enumerator.enumerate(5)
        first_keys = [program_key(program) for program in first]
        self.assertEqual(first, second)
        self.assertEqual(len(first_keys), len(set(first_keys)))

    def test_prediction_enumerator_cannot_read_future_target(self) -> None:
        programs = ProgramEnumerator(readable_offsets=(-1, 0)).enumerate(5)
        self.assertTrue(programs)
        for program in programs:
            self.assertTrue(set(iter_read_offsets(program)).issubset({-1, 0}))

    def test_unregistered_offset_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ProgramEnumerator(readable_offsets=(-2, 0))


class SearchTests(unittest.TestCase):
    def test_search_finds_an_exact_short_predictor_without_future_read(self) -> None:
        report = NextValueProgramSearch(maximum_nodes=3, top_k=5).search(
            affine_observation()
        )
        best = report.top_candidates[0]
        self.assertAlmostEqual(best.train_mse, 0.0)
        self.assertAlmostEqual(best.validation_mse, 0.0)
        self.assertTrue(set(iter_read_offsets(best.program)).issubset({-1, 0}))
        self.assertNotIn(1, set(iter_read_offsets(best.program)))
        self.assertEqual(report.target_offset, 1)

    def test_search_report_is_deterministic(self) -> None:
        search = NextValueProgramSearch(maximum_nodes=3, top_k=5)
        first = search.search(affine_observation()).to_dict()
        second = search.search(affine_observation()).to_dict()
        self.assertEqual(first, second)

    def test_search_uses_disjoint_train_and_validation_counts(self) -> None:
        observation = affine_observation()
        report = NextValueProgramSearch(maximum_nodes=3).search(observation)
        valid_examples = len(observation.sequence_values) - 2
        self.assertEqual(
            report.train_example_count + report.validation_example_count,
            valid_examples,
        )
        self.assertGreater(report.train_example_count, 0)
        self.assertGreater(report.validation_example_count, 0)

    def test_too_few_examples_are_rejected(self) -> None:
        environment = HiddenSequenceEnvironment(
            SequenceWorldSpec("affine", (0.0, 1.0), 4),
            seed=1,
            secret=b"search-test-secret",
        )
        with self.assertRaises(ValueError):
            NextValueProgramSearch(maximum_nodes=3).search(environment.observe(4))


if __name__ == "__main__":
    unittest.main()

