from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import FormulaRoomError, FormulaSuccessRoom
from akgm_n0.learner import relation_add, relation_value


FIXED_TIME = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


class FormulaSuccessRoomTests(unittest.TestCase):
    def test_only_verified_formula_can_enter_room(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            room = FormulaSuccessRoom(Path(temporary_directory) / "formulas.jsonl")
            with self.assertRaises(FormulaRoomError):
                room.record(
                    relation_add(relation_value(), relation_value()),
                    operation_id="ROP-test",
                    parent_operation_ids=("r_add",),
                    validation_scope="test",
                    knowledge_status="fit_passed",
                    evidence={"probe_count": 4},
                )

    def test_record_is_idempotent_reloadable_and_hash_chained(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "formulas.jsonl"
            room = FormulaSuccessRoom(path, clock=lambda: FIXED_TIME)
            formula = relation_add(relation_value(), relation_value())
            arguments = {
                "operation_id": "ROP-test",
                "parent_operation_ids": ("r_add",),
                "validation_scope": "test-scope",
                "knowledge_status": "bounded",
                "evidence": {"probe_count": 4},
            }
            first = room.record(formula, **arguments)
            second = room.record(formula, **arguments)
            self.assertEqual(first.room_record_id, second.room_record_id)
            self.assertEqual(len(room.records), 1)
            reloaded = FormulaSuccessRoom(path)
            self.assertEqual(reloaded.records, room.records)
            event = json.loads(path.read_text(encoding="utf-8"))
            event["operation_id"] = "ROP-tampered"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaises(FormulaRoomError):
                FormulaSuccessRoom(path)

    def test_disqualification_preserves_history_but_removes_active_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "formulas.jsonl"
            room = FormulaSuccessRoom(path, clock=lambda: FIXED_TIME)
            record = room.record(
                relation_add(relation_value(), relation_value()),
                operation_id="ROP-test",
                parent_operation_ids=("r_add",),
                validation_scope="test-scope",
                knowledge_status="bounded",
                evidence={"probe_count": 4},
            )
            room.disqualify(
                record.room_record_id,
                reason="shared_underlying_logic",
                evidence={"same_logic_as": "SF-earlier"},
            )
            self.assertEqual(room.records, ())
            self.assertEqual(len(room.historical_records), 1)
            self.assertIn(record.room_record_id, room.disqualifications)
            reloaded = FormulaSuccessRoom(path)
            self.assertEqual(reloaded.records, ())
            self.assertEqual(len(reloaded.historical_records), 1)


if __name__ == "__main__":
    unittest.main()
