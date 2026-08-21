from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.contracts import (
    METAMACHINE_PUBLIC_PATHS,
    OPERATION_GROWTH_PUBLIC_PATHS,
    PUBLIC_CONTRACT_PATHS,
    RELATION_GROWTH_PUBLIC_PATHS,
    load_learner_contract,
    load_primitive_manifest,
)
from akgm_n0.leakage_audit import audit_public_contracts, load_policy
from akgm_n0.learner_bundle import LearnerBundleError, build_learner_bundle


class ContractTests(unittest.TestCase):
    def test_public_contracts_are_valid_and_version_aligned(self) -> None:
        contract = load_learner_contract()
        manifest = load_primitive_manifest()
        self.assertEqual(contract["protocol_version"], manifest["protocol_version"])
        self.assertEqual(contract["visibility"], "learner_visible")
        self.assertEqual(manifest["visibility"], "learner_visible")

    def test_public_contracts_contain_no_registered_target_leakage(self) -> None:
        self.assertEqual(audit_public_contracts(), [])

    def test_policy_audits_only_declared_public_contracts(self) -> None:
        policy = load_policy()
        policy_paths = {
            (PROJECT_ROOT / path).resolve() for path in policy["public_paths"]
        }
        self.assertEqual(
            policy_paths,
            {
                path.resolve()
                for path in (
                    *PUBLIC_CONTRACT_PATHS,
                    *OPERATION_GROWTH_PUBLIC_PATHS,
                    *METAMACHINE_PUBLIC_PATHS,
                    *RELATION_GROWTH_PUBLIC_PATHS,
                )
            },
        )

    def test_sealed_benchmark_is_evaluator_only(self) -> None:
        path = PROJECT_ROOT / "evaluator" / "sealed_benchmark.yaml"
        with path.open("r", encoding="utf-8") as stream:
            benchmark = json.load(stream)
        self.assertEqual(benchmark["visibility"], "evaluator_only")
        self.assertFalse(path.is_relative_to(PROJECT_ROOT / "configs"))

    def test_initial_primitive_surface_is_exactly_registered(self) -> None:
        manifest = load_primitive_manifest()
        primitive_ids = {item["id"] for item in manifest["primitives"]}
        self.assertEqual(
            primitive_ids,
            {
                "p_read_offset",
                "p_add",
                "p_subtract",
                "p_scalar_parameter",
                "p_compose",
            },
        )

    def test_blind_feedback_is_empty(self) -> None:
        contract = load_learner_contract()
        self.assertEqual(
            contract["feedback_interface"]["blind_feedback_during_search"], []
        )

    def test_learner_bundle_is_allowlist_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "learner"
            manifest = build_learner_bundle(destination)
            bundled_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            self.assertEqual(
                bundled_files,
                {
                    "bundle_manifest.json",
                    "configs/learner_contract.yaml",
                    "configs/primitive_manifest.yaml",
                },
            )
            self.assertEqual(len(manifest["allowlisted_files"]), 2)
            self.assertFalse((destination / "evaluator").exists())

    def test_learner_bundle_rejects_nonempty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "learner"
            destination.mkdir()
            (destination / "unexpected.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(LearnerBundleError):
                build_learner_bundle(destination)

    def test_operation_growth_bundle_is_separate_from_gen0(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "learner"
            manifest = build_learner_bundle(destination, profile="operation_growth")
            bundled_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            self.assertEqual(manifest["source_protocol"], "operation-growth-v0.1")
            self.assertIn(
                "configs/operation_growth/primitive_manifest.yaml", bundled_files
            )
            self.assertNotIn("configs/primitive_manifest.yaml", bundled_files)

    def test_metamachine_bundle_contains_no_gen0_or_iteration_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "learner"
            manifest = build_learner_bundle(destination, profile="metamachine")
            bundled_files = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            }
            self.assertEqual(manifest["source_protocol"], "metamachine-gen1-v0.1")
            self.assertIn("configs/metamachine/substrate_manifest.yaml", bundled_files)
            self.assertNotIn("configs/primitive_manifest.yaml", bundled_files)
            self.assertNotIn(
                "configs/operation_growth/primitive_manifest.yaml", bundled_files
            )

    def test_relation_growth_bundle_declares_unordered_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "learner"
            manifest = build_learner_bundle(destination, profile="relation_growth")
            contract = json.loads(
                (destination / "configs/relation_growth/learner_contract.yaml").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["source_protocol"], "relation-growth-v0.1")
            self.assertFalse(
                contract["input_interface"]["input_order_has_semantics"]
            )


if __name__ == "__main__":
    unittest.main()
