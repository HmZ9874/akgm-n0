from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    HiddenSequenceEnvironment,
    IndependentVerifier,
    SequenceWorldSpec,
    VerificationCase,
)
from akgm_n0.learner import NextValueProgramSearch, read_offset


SECRET = b"verifier-test-secret"


def observation(spec: SequenceWorldSpec, seed: int):
    return HiddenSequenceEnvironment(spec, seed=seed, secret=SECRET).observe(spec.length)


def exact_affine_candidate():
    source = observation(SequenceWorldSpec("affine", (2.0, 3.0), 12), 10)
    return NextValueProgramSearch(maximum_nodes=3, top_k=1).search(source).top_candidates[0].program


class VerifierTests(unittest.TestCase):
    def test_candidate_is_bounded_when_adversarial_world_supplies_counterexamples(self) -> None:
        cases = [
            VerificationCase.create(
                scope="source_holdout",
                observation=observation(SequenceWorldSpec("affine", (7.0, 3.0), 12), 11),
                refit_prefix_length=6,
                required_for_validity=True,
            ),
            VerificationCase.create(
                scope="registered_ood",
                observation=observation(SequenceWorldSpec("affine", (100.0, -7.0), 12), 12),
                refit_prefix_length=6,
                required_for_validity=True,
            ),
            VerificationCase.create(
                scope="adversarial_challenge",
                observation=observation(SequenceWorldSpec("polynomial2", (1.0, 0.0, 1.0), 12), 13),
                refit_prefix_length=6,
                required_for_validity=False,
            ),
        ]
        report = IndependentVerifier().verify(exact_affine_candidate(), cases)
        self.assertEqual(report.status, "bounded")
        self.assertTrue(report.case_results[0].passed)
        self.assertTrue(report.case_results[1].passed)
        self.assertFalse(report.case_results[2].passed)
        self.assertGreater(len(report.counterexamples), 0)
        first = report.counterexamples[0].to_dict()
        self.assertEqual(
            set(first),
            {
                "case_id",
                "index",
                "readable_values",
                "predicted_value",
                "observed_value",
                "absolute_error",
            },
        )

    def test_required_failure_rejects_candidate(self) -> None:
        case = VerificationCase.create(
            scope="source_holdout",
            observation=observation(SequenceWorldSpec("affine", (1.0, 5.0), 10), 20),
            refit_prefix_length=5,
            required_for_validity=True,
        )
        report = IndependentVerifier().verify(read_offset(0), [case])
        self.assertEqual(report.status, "rejected")
        self.assertGreater(len(report.counterexamples), 0)

    def test_all_registered_cases_can_verify_candidate(self) -> None:
        cases = [
            VerificationCase.create(
                scope="source_holdout",
                observation=observation(SequenceWorldSpec("affine", (1.0, 3.0), 10), 30),
                refit_prefix_length=5,
                required_for_validity=True,
            ),
            VerificationCase.create(
                scope="registered_ood",
                observation=observation(SequenceWorldSpec("affine", (-500.0, 17.0), 10), 31),
                refit_prefix_length=5,
                required_for_validity=True,
            ),
        ]
        report = IndependentVerifier().verify(exact_affine_candidate(), cases)
        self.assertEqual(report.status, "verified")
        self.assertFalse(report.counterexamples)

    def test_verifier_rejects_structural_target_read(self) -> None:
        case = VerificationCase.create(
            scope="source_holdout",
            observation=observation(SequenceWorldSpec("affine", (1.0, 2.0), 10), 40),
            refit_prefix_length=5,
            required_for_validity=True,
        )
        with self.assertRaises(ValueError):
            IndependentVerifier().verify(read_offset(1), [case])


if __name__ == "__main__":
    unittest.main()

