from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from akgm_n0.evaluator import (
    NestedFoundationRoom,
    PartitionFoundationRoom,
    verify_nested_foundation_semantic,
    verify_partition_foundation_semantic,
)
from akgm_n0.learner import (
    AnonymousCycleExecutor,
    GroupCycleSearch,
    GroupExample,
    NestedCycleSearch,
    NestedExample,
    NestedFoundationSemantic,
    PartitionFoundationSemantic,
    cartesian_observation,
    grouping_observation,
    opaque_symbols,
)


ROOT = Path(__file__).resolve().parents[1]


class NestedArithmeticFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/nested_arithmetic_latest.json").read_text(encoding="utf-8")
        )
        cls.nested = NestedFoundationSemantic.from_dict(
            cls.report["discoveries"][0]["semantic"]
        )
        cls.partition = PartitionFoundationSemantic.from_dict(
            cls.report["discoveries"][1]["semantic"]
        )

    def test_nested_search_has_one_exact_program(self) -> None:
        examples = []
        for index, (a, b) in enumerate(((0, 3), (3, 0), (1, 1), (2, 4), (5, 3))):
            left = opaque_symbols(f"A{index}", a)
            right = opaque_symbols(f"B{index}", b)
            examples.append(NestedExample((left, right), cartesian_observation(left, right)))
        search = NestedCycleSearch().search("TEST-NESTED", examples)
        self.assertEqual(search.candidates_evaluated, 20)
        self.assertEqual(sum(item.exact for item in search.candidates), 1)
        self.assertEqual(search.selected.program.program_id, self.nested.program.program_id)

    def test_group_search_has_one_exact_program(self) -> None:
        examples = []
        for index, (a, b) in enumerate(((0, 1), (1, 2), (6, 2), (7, 3), (23, 5))):
            source = opaque_symbols(f"S{index}", a)
            stencil = opaque_symbols(f"T{index}", b)
            completed, residue = grouping_observation(source, stencil)
            examples.append(GroupExample((source, stencil), completed, residue))
        search = GroupCycleSearch().search("TEST-GROUP", examples)
        self.assertEqual(search.candidates_evaluated, 24)
        self.assertEqual(sum(item.exact for item in search.candidates), 1)
        self.assertEqual(search.selected.program.program_id, self.partition.program.program_id)

    def test_universal_proofs_and_hidden_cases_pass(self) -> None:
        nested_proof = verify_nested_foundation_semantic(self.nested)
        partition_proof = verify_partition_foundation_semantic(self.partition)
        self.assertTrue(nested_proof["passed"])
        self.assertTrue(partition_proof["passed"])
        self.assertEqual(sum(item["passed"] for item in nested_proof["obligations"]), 13)
        self.assertEqual(sum(item["passed"] for item in partition_proof["obligations"]), 16)
        self.assertEqual(sum(item["passed"] for item in nested_proof["case_results"]), 12)
        self.assertEqual(sum(item["passed"] for item in partition_proof["case_results"]), 13)

    def test_structural_outputs_decode_to_expected_cardinalities(self) -> None:
        left = opaque_symbols("L", 6)
        right = opaque_symbols("R", 7)
        nested_result = AnonymousCycleExecutor().execute_nested(self.nested.program, (left, right))
        self.assertEqual(len(nested_result.output), 42)
        source = opaque_symbols("Q", 31)
        stencil = opaque_symbols("D", 7)
        group_result = AnonymousCycleExecutor().execute_group(self.partition.program, (source, stencil))
        self.assertEqual((len(group_result.output), len(group_result.residue)), (4, 3))

    def test_empty_stencil_is_rejected_and_tampering_fails_proof(self) -> None:
        rejected = AnonymousCycleExecutor().execute_group(
            self.partition.program, (opaque_symbols("S", 5), ())
        )
        self.assertFalse(rejected.halted)
        mutated = replace(
            self.nested,
            program=replace(self.nested.program, rewind_inner=False),
        )
        self.assertFalse(verify_nested_foundation_semantic(mutated)["passed"])

    def test_success_rooms_replay(self) -> None:
        nested_room = NestedFoundationRoom(
            ROOT / "artifacts/foundation/success/nested_semantics.jsonl"
        )
        partition_room = PartitionFoundationRoom(
            ROOT / "artifacts/foundation/success/partition_semantics.jsonl"
        )
        self.assertEqual(len(nested_room.records), 1)
        self.assertEqual(len(partition_room.records), 1)
        self.assertEqual(nested_room.records[0]["semantic"]["semantic_id"], "NSEM-52a33255cdea401f")
        self.assertEqual(partition_room.records[0]["semantic"]["semantic_id"], "PSEM-b6863ee740b31807")


if __name__ == "__main__":
    unittest.main()
