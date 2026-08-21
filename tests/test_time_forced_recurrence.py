from __future__ import annotations

import json
import unittest
from pathlib import Path

from akgm_n0.evaluator import (
    UniversalFormulaCertificate,
    UniversalFormulaRoom,
    UniversalProofVerifier,
)
from akgm_n0.learner import SemanticExtendedExecutor, SemanticExtendedProgram


ROOT = Path(__file__).resolve().parents[1]


def hidden_relation(row):
    q, n, r, state, p = (int(value) for value in row)
    for clock in range(n):
        state = p * state + q * clock + r
    return float(state)


class TimeForcedRecurrenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/time_forced_recurrence_latest.json").read_text(
                encoding="utf-8"
            )
        )

    def test_anonymous_search_found_free_clock_coupled_recurrence(self) -> None:
        report = self.report
        self.assertTrue(all(gate["passed"] for gate in report["gates"]))
        self.assertEqual(report["experiment"]["self_selected_query_count"], 1)
        self.assertEqual(sum(item["passed"] for item in report["sealed_results"]), 6)
        self.assertFalse(report["learner_received"]["formula_name"])
        self.assertFalse(report["learner_received"]["input_role_map"])
        program = SemanticExtendedProgram.from_dict(report["candidate"]["program"])
        executor = SemanticExtendedExecutor()
        for item in report["sealed_results"]:
            row = tuple(item["inputs"])
            self.assertEqual(executor.execute(program, row).output_value, hidden_relation(row))

    def test_new_strict_formula_and_universal_proof_replay(self) -> None:
        report = self.report
        self.assertEqual(report["strict_formula_total_after"], 34)
        self.assertEqual(report["room_proof_obligation_passed_count"], 487)
        self.assertEqual(report["room_proof_obligation_count"], 487)
        room = UniversalFormulaRoom(
            ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
        )
        self.assertEqual(len(room.records), 34)
        record = next(
            item
            for item in room.records
            if item.room_record_id == report["strict_room_record"]["room_record_id"]
        )
        program = SemanticExtendedProgram.from_dict(dict(record.program))
        certificate = UniversalFormulaCertificate.from_dict(record.certificate)
        replay = UniversalProofVerifier().verify(program, certificate)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.to_dict(), record.verification)


if __name__ == "__main__":
    unittest.main()
