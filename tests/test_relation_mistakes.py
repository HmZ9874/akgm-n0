from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    RelationMistakeLibrary,
    RelationMistakeLibraryError,
)
from akgm_n0.learner import (
    NumericCollectionObservation,
    RelationProgramSearch,
    relation_add,
    relation_constant,
    relation_subtract,
    relation_value,
)


FIXED_TIME = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


def observation():
    values = (3, 7, 15, 31, 63, 127, 255)
    return NumericCollectionObservation.create(
        opaque_session_id="RELATION-MISTAKE-TEST",
        numeric_values=values,
        validity_mask=[True] * len(values),
        action_receipt="TEST",
    )


class RelationMistakeLibraryTests(unittest.TestCase):
    def test_equivalent_affine_trees_are_blocked_and_reloaded(self) -> None:
        first = relation_add(relation_value(), relation_constant(4))
        equivalent = relation_subtract(relation_value(), relation_constant(-4))
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "relation_mistakes.jsonl"
            library = RelationMistakeLibrary(path, clock=lambda: FIXED_TIME)
            record = library.record(
                first,
                objective_id="unordered_relation_compression",
                failed_scope="supplied_collection",
                condition_key="set-1",
                counterexamples=({"source": 7.0, "result": 11.0},),
                source_candidate_id="REL-first",
            )
            reloaded = RelationMistakeLibrary(path)

            self.assertEqual(
                reloaded.find_equivalent(
                    equivalent,
                    objective_id="unordered_relation_compression",
                    failed_scope="supplied_collection",
                    condition_key="set-1",
                )[0].mistake_id,
                record.mistake_id,
            )

    def test_search_filters_a_recorded_semantic_family(self) -> None:
        rejected = relation_subtract(relation_value(), relation_value())
        with tempfile.TemporaryDirectory() as temporary_directory:
            library = RelationMistakeLibrary(
                Path(temporary_directory) / "relation_mistakes.jsonl"
            )
            arguments = {
                "objective_id": "unordered_relation_compression",
                "failed_scope": "supplied_collection",
                "condition_key": "set-1",
            }
            library.record(
                rejected,
                **arguments,
                counterexamples=({"reason": "no_observed_edges"},),
                source_candidate_id="REL-zero",
            )
            report = RelationProgramSearch(
                maximum_nodes=5,
                candidate_gate=library.candidate_gate(**arguments),
            ).search(observation())

            self.assertGreater(report.programs_filtered, 0)
            for candidate in report.top_candidates:
                self.assertFalse(
                    library.find_equivalent(candidate.program, **arguments)
                )

    def test_chain_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "relation_mistakes.jsonl"
            library = RelationMistakeLibrary(path, clock=lambda: FIXED_TIME)
            library.record(
                relation_subtract(relation_value(), relation_value()),
                objective_id="unordered_relation_compression",
                failed_scope="supplied_collection",
                condition_key="set-1",
                counterexamples=({"reason": "no_observed_edges"},),
                source_candidate_id="REL-zero",
            )
            event = json.loads(path.read_text(encoding="utf-8"))
            event["condition_key"] = "tampered"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")

            with self.assertRaises(RelationMistakeLibraryError):
                RelationMistakeLibrary(path)


if __name__ == "__main__":
    unittest.main()
