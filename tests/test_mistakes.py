from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import MistakeLibrary, MistakeLibraryError
from akgm_n0.learner import NextValueProgramSearch, add, parameter, read_offset, subtract
from test_search import affine_observation


FIXED_TIME = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
OBJECTIVE = NextValueProgramSearch.OBJECTIVE_ID
CONDITION = "registered_curve_challenge_v0.1"


class MistakeLibraryTests(unittest.TestCase):
    def test_structurally_different_parameter_families_match(self) -> None:
        first = subtract(read_offset(0), parameter(0))
        equivalent = add(parameter(0), read_offset(0))
        with tempfile.TemporaryDirectory() as temporary_directory:
            library = MistakeLibrary(
                Path(temporary_directory) / "mistakes.jsonl",
                clock=lambda: FIXED_TIME,
            )
            record = library.record(
                first,
                objective_id=OBJECTIVE,
                failed_scope="adversarial_challenge",
                condition_key=CONDITION,
                counterexamples=({"input": [1.0, 2.0], "observed": 5.0},),
                source_candidate_id="CAND-first",
            )
            hits = library.find_equivalent(
                equivalent,
                objective_id=OBJECTIVE,
                failed_scope="adversarial_challenge",
                condition_key=CONDITION,
            )
            self.assertEqual([item.mistake_id for item in hits], [record.mistake_id])

    def test_same_family_is_not_blocked_outside_recorded_condition(self) -> None:
        program = subtract(read_offset(0), parameter(0))
        with tempfile.TemporaryDirectory() as temporary_directory:
            library = MistakeLibrary(Path(temporary_directory) / "mistakes.jsonl")
            library.record(
                program,
                objective_id=OBJECTIVE,
                failed_scope="adversarial_challenge",
                condition_key=CONDITION,
                counterexamples=({"error": 1.0},),
                source_candidate_id="CAND-first",
            )
            self.assertEqual(
                library.find_equivalent(
                    program,
                    objective_id=OBJECTIVE,
                    failed_scope="registered_ood",
                    condition_key=CONDITION,
                ),
                (),
            )

    def test_search_filters_recorded_family_before_scoring(self) -> None:
        program = subtract(read_offset(0), parameter(0))
        with tempfile.TemporaryDirectory() as temporary_directory:
            library = MistakeLibrary(Path(temporary_directory) / "mistakes.jsonl")
            library.record(
                program,
                objective_id=OBJECTIVE,
                failed_scope="adversarial_challenge",
                condition_key=CONDITION,
                counterexamples=({"error": 1.0},),
                source_candidate_id="CAND-first",
            )
            report = NextValueProgramSearch(
                maximum_nodes=3,
                candidate_gate=library.candidate_gate(
                    objective_id=OBJECTIVE,
                    failed_scope="adversarial_challenge",
                    condition_key=CONDITION,
                ),
            ).search(affine_observation())
            self.assertGreater(report.programs_filtered, 0)
            for candidate in report.top_candidates:
                self.assertFalse(
                    library.find_equivalent(
                        candidate.program,
                        objective_id=OBJECTIVE,
                        failed_scope="adversarial_challenge",
                        condition_key=CONDITION,
                    )
                )

    def test_duplicate_record_is_idempotent_and_chain_detects_tampering(self) -> None:
        program = subtract(read_offset(0), parameter(0))
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "mistakes.jsonl"
            library = MistakeLibrary(path, clock=lambda: FIXED_TIME)
            arguments = {
                "objective_id": OBJECTIVE,
                "failed_scope": "adversarial_challenge",
                "condition_key": CONDITION,
                "counterexamples": ({"error": 1.0},),
                "source_candidate_id": "CAND-first",
            }
            first = library.record(program, **arguments)
            second = library.record(program, **arguments)
            self.assertEqual(first.mistake_id, second.mistake_id)
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)
            event = json.loads(path.read_text(encoding="utf-8"))
            event["condition_key"] = "tampered"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaises(MistakeLibraryError):
                MistakeLibrary(path)


if __name__ == "__main__":
    unittest.main()
