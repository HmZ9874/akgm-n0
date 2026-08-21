from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.learner import (
    NumericCollectionObservation,
    RelationExecutor,
    RelationOperationLibrary,
    RelationProgramSearch,
    compose_relation,
    relation_add,
    relation_constant,
    relation_value,
)


def observation(values):
    return NumericCollectionObservation.create(
        opaque_session_id="RELATION-TEST",
        numeric_values=values,
        validity_mask=[True] * len(values),
        action_receipt="TEST",
    )


class RelationDiscoveryTests(unittest.TestCase):
    def test_executor_uses_an_evidence_constant_without_multiplication(self) -> None:
        program = relation_add(
            relation_add(relation_value(), relation_value()),
            relation_constant(1),
        )

        self.assertEqual(RelationExecutor().evaluate(program, 15), 31.0)

    def test_public_collection_has_no_order_or_output_field(self) -> None:
        public = observation((2, 8, 16, 64, 4)).to_public_dict()
        self.assertEqual(
            set(public),
            {"opaque_session_id", "numeric_values", "validity_mask", "action_receipt"},
        )
        self.assertNotIn("output_values", public)

    def test_search_discovers_short_order_invariant_executable_operation(self) -> None:
        search = RelationProgramSearch(maximum_nodes=7, maximum_composition_steps=6)
        first = search.search(observation((2, 8, 16, 64, 4)))
        second = search.search(observation((64, 4, 2, 16, 8)))
        selected = first.top_candidates[0]
        self.assertEqual(selected.candidate_id, second.top_candidates[0].candidate_id)
        self.assertEqual(
            selected.program.to_dict(),
            {
                "op": "r_add",
                "args": [{"op": "r_value"}, {"op": "r_value"}],
            },
        )
        self.assertEqual(
            [edge.to_dict() for edge in selected.direct_edges],
            [
                {"source": 2.0, "target": 4.0},
                {"source": 4.0, "target": 8.0},
                {"source": 8.0, "target": 16.0},
            ],
        )

    def test_discovered_operation_can_compose_into_a_new_executable(self) -> None:
        candidate = RelationProgramSearch().search(
            observation((2, 8, 16, 64, 4))
        ).top_candidates[0]
        composed = compose_relation(candidate.program, candidate.program)
        executor = RelationExecutor()
        self.assertEqual(executor.evaluate(composed, 2), 8.0)
        self.assertEqual(executor.evaluate(composed, 4), 16.0)
        library = RelationOperationLibrary(executor)
        promoted = library.promote(candidate.program)
        composed_promoted = library.compose(
            promoted.operation_id, promoted.operation_id
        )
        self.assertTrue(promoted.operation_id.startswith("ROP-"))
        self.assertNotEqual(promoted.operation_id, composed_promoted.operation_id)
        self.assertEqual(library.execute(promoted.operation_id, 16), 32.0)
        self.assertEqual(library.execute(composed_promoted.operation_id, 16), 64.0)

    def test_search_builds_working_memory_and_connects_all_members(self) -> None:
        values = (3, 7, 15, 31, 63, 127, 255)
        search = RelationProgramSearch(maximum_nodes=5, top_k=10)
        first = search.search(observation(values))
        reversed_result = search.search(observation(tuple(reversed(values))))
        selected = first.top_candidates[0]

        self.assertEqual(selected.candidate_id, reversed_result.top_candidates[0].candidate_id)
        self.assertEqual(len(selected.direct_edges), 6)
        self.assertEqual(selected.best_chain, tuple(float(value) for value in values))
        constant_one = [
            item for item in first.evidence_constants if item["value"] == 1.0
        ]
        self.assertEqual(len(constant_one), 1)
        self.assertEqual(constant_one[0]["derivation_depth"], 2)
        self.assertEqual(
            [RelationExecutor().evaluate(selected.program, value) for value in values[:-1]],
            [float(value) for value in values[1:]],
        )

    def test_five_composed_operations_have_distinct_behavior(self) -> None:
        candidate = RelationProgramSearch().search(
            observation((2, 8, 16, 64, 4))
        ).top_candidates[0]
        library = RelationOperationLibrary()
        base = library.promote(candidate.program)
        operations = [base]
        for _ in range(4):
            operations.append(
                library.compose(base.operation_id, operations[-1].operation_id)
            )
        self.assertEqual(len({item.operation_id for item in operations}), 5)
        outputs = [library.execute(item.operation_id, 3.0) for item in operations]
        self.assertEqual(outputs, [6.0, 12.0, 24.0, 48.0, 96.0])


if __name__ == "__main__":
    unittest.main()
