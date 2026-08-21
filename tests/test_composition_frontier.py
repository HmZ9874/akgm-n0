from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import FormulaSuccessRoom, UniversalFormulaRoom
from akgm_n0.learner import (
    CompositionExecutor,
    CompositionGraphProgram,
    CompositionNode,
    InvalidReflectiveProgram,
    ReflectiveProgram,
    composition_logic_signature,
)


class CompositionFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (PROJECT_ROOT / "reports" / "data" / "composition_twenty_latest.json").read_text(
                encoding="utf-8"
            )
        )
        room = FormulaSuccessRoom(
            PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl"
        )
        cls.source_by_operation = {record.operation_id: record for record in room.records}

    def test_latest_batch_contains_twenty_distinct_exact_compositions(self) -> None:
        tasks = self.report["tasks"]
        self.assertEqual(len(tasks), 20)
        self.assertEqual(self.report["mistake_feedback_count"], 80)
        self.assertTrue(all(gate["passed"] for gate in self.report["gates"]))
        programs = [CompositionGraphProgram.from_dict(task["candidate"]["program"]) for task in tasks]
        self.assertEqual(len({composition_logic_signature(program) for program in programs}), 20)
        self.assertTrue(all(task["candidate"]["exact"] for task in tasks))

    def test_composition_executes_only_through_recorded_component_programs(self) -> None:
        program = CompositionGraphProgram.from_dict(self.report["tasks"][0]["candidate"]["program"])
        library = {
            operation_id: ReflectiveProgram.from_dict(dict(self.source_by_operation[operation_id].definition))
            for operation_id in program.component_operation_ids
        }
        self.assertEqual(CompositionExecutor(library).execute(program, (2,)).output_value, 81)

    def test_forward_reference_is_rejected(self) -> None:
        valid = CompositionGraphProgram.from_dict(self.report["tasks"][0]["candidate"]["program"])
        library = {
            operation_id: ReflectiveProgram.from_dict(dict(self.source_by_operation[operation_id].definition))
            for operation_id in valid.component_operation_ids
        }
        invalid = CompositionGraphProgram(
            (CompositionNode(valid.nodes[0].operation_id, ("node:0",)),)
        )
        with self.assertRaises(InvalidReflectiveProgram):
            CompositionExecutor(library).execute(invalid, (2,))

    def test_fifty_record_universal_room_replays_after_symbolic_substitution(self) -> None:
        room = UniversalFormulaRoom(
            PROJECT_ROOT / "artifacts" / "formula_rooms" / "universal" / "proven_formulas.jsonl"
        )
        self.assertEqual(len(room.records), 50)


if __name__ == "__main__":
    unittest.main()
