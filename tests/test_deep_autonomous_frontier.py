from __future__ import annotations

import json
import unittest
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from akgm_n0.evaluator import (
    ApproximationFrontierRoom,
    CanonicalFrontierRoom,
    FiniteMassRoom,
    JointFrontierRoom,
    PairedWeightedRoom,
    RatioFrontierRoom,
    RationalAlgebraRoom,
    RootFrontierRoom,
    WeightedFrontierRoom,
    verify_canonical_foundation_semantic,
    verify_finite_mass_semantic,
    verify_joint_foundation_semantic,
    verify_paired_weighted_semantic,
    verify_root_foundation_semantic,
    verify_approximation_foundation_semantic,
    verify_ratio_foundation_semantic,
    verify_rational_algebra_semantic,
    verify_weighted_foundation_semantic,
)
from akgm_n0.learner import (
    CanonicalFoundationSemantic,
    FiniteMassSemantic,
    JointFoundationSemantic,
    PairedWeightedSemantic,
    RootFoundationSemantic,
    RootExecutor,
    ApproximationFoundationSemantic,
    RatioFoundationSemantic,
    RationalAlgebraSemantic,
    WeightedFoundationSemantic,
    common_observation,
    normalized_event_mass,
    normalized_pair_observation,
    paired_center,
    weighted_center,
    exact_rational_boundary,
    interval_refinement,
)


ROOT = Path(__file__).resolve().parents[1]


class DeepAutonomousFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        paths = {
            "canonical": "autonomous_canonicalization_latest.json",
            "ratio": "autonomous_ratio_latest.json",
            "mass": "autonomous_finite_mass_latest.json",
            "joint": "autonomous_joint_latest.json",
            "weighted": "autonomous_weighted_latest.json",
            "rational": "autonomous_rational_latest.json",
            "paired": "autonomous_paired_latest.json",
            "root": "autonomous_exact_root_latest.json",
            "interval": "autonomous_interval_memory_latest.json",
        }
        cls.reports = {
            key: json.loads((ROOT / "reports/data" / name).read_text(encoding="utf-8"))
            for key, name in paths.items()
        }
        cls.semantics = {
            "canonical": CanonicalFoundationSemantic.from_dict(
                cls.reports["canonical"]["discovery"]["semantic"]
            ),
            "ratio": RatioFoundationSemantic.from_dict(
                cls.reports["ratio"]["discovery"]["semantic"]
            ),
            "mass": FiniteMassSemantic.from_dict(
                cls.reports["mass"]["derived_discovery"]["semantic"]
            ),
            "joint": JointFoundationSemantic.from_dict(
                cls.reports["joint"]["discovery"]["semantic"]
            ),
            "weighted": WeightedFoundationSemantic.from_dict(
                cls.reports["weighted"]["discovery"]["semantic"]
            ),
            "rational": RationalAlgebraSemantic.from_dict(
                cls.reports["rational"]["discovery"]["semantic"]
            ),
            "paired": PairedWeightedSemantic.from_dict(
                cls.reports["paired"]["discovery"]["semantic"]
            ),
            "root": RootFoundationSemantic.from_dict(
                cls.reports["root"]["discovery"]["semantic"]
            ),
            "interval": ApproximationFoundationSemantic.from_dict(
                cls.reports["interval"]["discovery"]["semantic"]
            ),
        }

    def test_every_persisted_deep_semantic_replays_its_independent_proof(self) -> None:
        verifiers = {
            "canonical": verify_canonical_foundation_semantic,
            "ratio": verify_ratio_foundation_semantic,
            "mass": verify_finite_mass_semantic,
            "joint": verify_joint_foundation_semantic,
            "weighted": verify_weighted_foundation_semantic,
            "rational": verify_rational_algebra_semantic,
            "paired": verify_paired_weighted_semantic,
            "root": verify_root_foundation_semantic,
            "interval": verify_approximation_foundation_semantic,
        }
        for key, verifier in verifiers.items():
            with self.subTest(stage=key):
                proof = verifier(self.semantics[key])
                self.assertTrue(proof["passed"])
                self.assertTrue(all(item["passed"] for item in proof["obligations"]))
                self.assertTrue(all(item["passed"] for item in proof["case_results"]))
                self.assertFalse(proof["finite_sampling_used_as_proof"])

    def test_foundation_levels_are_monotone_and_derived_mass_does_not_inflate_them(self) -> None:
        self.assertEqual(self.reports["canonical"]["discovery"]["foundation_level"], 9)
        self.assertEqual(self.reports["ratio"]["discovery"]["foundation_level"], 10)
        self.assertFalse(self.reports["mass"]["derived_discovery"]["counts_as_new_foundation"])
        self.assertEqual(self.reports["mass"]["capability_graph"]["verified_foundation_count"], 10)
        self.assertEqual(self.reports["joint"]["discovery"]["foundation_level"], 11)
        self.assertEqual(self.reports["weighted"]["discovery"]["foundation_level"], 12)
        self.assertEqual(self.reports["rational"]["discovery"]["foundation_level"], 13)
        self.assertEqual(self.reports["paired"]["discovery"]["foundation_level"], 14)
        self.assertEqual(self.reports["root"]["discovery"]["foundation_level"], 15)
        self.assertEqual(self.reports["interval"]["discovery"]["foundation_level"], 16)

    def test_searches_were_anonymous_and_have_unique_selected_exact_programs(self) -> None:
        for key in ("canonical", "ratio", "joint", "weighted", "paired", "root", "interval"):
            with self.subTest(stage=key):
                discovery = self.reports[key]["discovery"]
                self.assertFalse(discovery["name_given_to_search"])
                self.assertGreater(self.reports[key]["search"]["candidate_count"], 1)
                self.assertGreaterEqual(self.reports[key]["search"]["exact_candidate_count"], 1)
        self.assertEqual(self.reports["mass"]["search"]["candidate_count"], 24)
        self.assertEqual(self.reports["mass"]["search"]["exact_candidate_count"], 1)
        self.assertFalse(self.reports["mass"]["derived_discovery"]["counts_as_new_foundation"])
        rational = self.reports["rational"]
        self.assertFalse(rational["discovery"]["name_given_to_search"])
        self.assertEqual(rational["searches"]["difference"]["candidate_count"], 60)
        self.assertEqual(rational["searches"]["square"]["candidate_count"], 60)

    def test_normalizers_and_accumulators_generalize_beyond_training_examples(self) -> None:
        normalized_part, normalized_whole = normalized_pair_observation(84, 126)
        self.assertEqual((len(normalized_part), len(normalized_whole)), (2, 3))
        self.assertEqual(normalized_event_mass(35, 100), (7, 20))
        universe = (0, 1, 2, 3, 4, 5, 6, 8)
        self.assertEqual(common_observation(universe, (1, 2, 3, 5, 8), (0, 2, 4, 5, 6)), (2, 5))
        records = ((-3, 2), (5, 2), (1, 4))
        self.assertEqual(Fraction(*weighted_center(records)), Fraction(1, 1))
        pairs = (((-2, 1), (-3, 1), 1), ((2, 1), (3, 1), 1))
        self.assertEqual(Fraction(*paired_center(pairs)), Fraction(6, 1))
        self.assertEqual(exact_rational_boundary((200, 450)), (2, 3))
        self.assertIsNone(exact_rational_boundary((2, 1)))
        lower, upper = interval_refinement((2, 1), 12)
        self.assertLessEqual(Fraction(*lower) ** 2, 2)
        self.assertGreaterEqual(Fraction(*upper) ** 2, 2)
        self.assertEqual(Fraction(*upper) - Fraction(*lower), Fraction(1, 2048))

    def test_covariance_layer_preserves_symmetry_and_self_variance(self) -> None:
        records = (
            ((-3, 2), (2, 3), 2),
            ((1, 2), (-2, 3), 3),
            ((3, 2), (2, 3), 1),
        )
        swapped = tuple((right, left, weight) for left, right, weight in records)
        self.assertEqual(paired_center(records), paired_center(swapped))
        self_records = tuple((left, left, weight) for left, _, weight in records)
        expected = sum(Fraction(*left) ** 2 * weight for left, _, weight in records) / sum(
            weight for _, _, weight in records
        )
        self.assertEqual(Fraction(*paired_center(self_records)), expected)

    def test_semantic_id_or_program_tampering_is_rejected_at_every_stage(self) -> None:
        verifiers = {
            "canonical": verify_canonical_foundation_semantic,
            "ratio": verify_ratio_foundation_semantic,
            "mass": verify_finite_mass_semantic,
            "joint": verify_joint_foundation_semantic,
            "weighted": verify_weighted_foundation_semantic,
            "rational": verify_rational_algebra_semantic,
            "paired": verify_paired_weighted_semantic,
            "root": verify_root_foundation_semantic,
            "interval": verify_approximation_foundation_semantic,
        }
        for key, verifier in verifiers.items():
            with self.subTest(stage=key):
                forged = replace(self.semantics[key], semantic_id="TAMPERED")
                self.assertFalse(verifier(forged)["passed"])

    def test_each_next_frontier_is_machine_recorded_and_not_posthoc_named(self) -> None:
        expected = {
            "canonical": "normalized_ratio_representation",
            "mass": "joint_event_intersection",
            "joint": "weighted_sum_accumulator",
            "weighted": "signed_rational_arithmetic",
            "rational": "paired_weighted_accumulator",
            "paired": "rational_square_root_normalizer",
            "root": "ordered_rational_approximation_memory",
            "interval": "completion_equivalence_limit_object",
        }
        for key, missing in expected.items():
            with self.subTest(stage=key):
                frontier = self.reports[key]["next_frontier"]
                self.assertEqual(frontier["missing_dependency"], missing)
                self.assertIsNone(frontier["posthoc_math_name"])

    def test_all_deep_success_rooms_reload_and_replay_hash_chains(self) -> None:
        foundation = ROOT / "artifacts/foundation/success"
        derived = ROOT / "artifacts/derived/success"
        rooms = (
            CanonicalFrontierRoom(foundation / "canonical_frontier_semantics.jsonl"),
            RatioFrontierRoom(foundation / "ratio_frontier_semantics.jsonl"),
            FiniteMassRoom(derived / "finite_mass_semantics.jsonl"),
            JointFrontierRoom(foundation / "joint_frontier_semantics.jsonl"),
            WeightedFrontierRoom(foundation / "weighted_frontier_semantics.jsonl"),
            RationalAlgebraRoom(foundation / "rational_algebra_semantics.jsonl"),
            PairedWeightedRoom(foundation / "paired_weighted_semantics.jsonl"),
            RootFrontierRoom(foundation / "exact_root_semantics.jsonl"),
            ApproximationFrontierRoom(foundation / "approximation_memory_semantics.jsonl"),
        )
        self.assertEqual(tuple(len(room.records) for room in rooms), (1, 1, 1, 1, 1, 1, 1, 2, 2))

    def test_root_scan_charges_each_outer_check_and_inner_addition(self) -> None:
        semantic = self.semantics["root"]
        self.assertEqual(semantic.program.token_accounting_version, 1)
        execution = RootExecutor().execute(semantic.program, (49, 64))
        self.assertTrue(execution.halted)
        self.assertEqual(execution.output, (7, 8))
        self.assertEqual(execution.primitive_execution_tokens, 91)


if __name__ == "__main__":
    unittest.main()
