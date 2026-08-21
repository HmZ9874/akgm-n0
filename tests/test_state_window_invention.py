from __future__ import annotations

import json
import unittest
from pathlib import Path

from akgm_n0.evaluator import UniversalFormulaRoom, verify_state_window_semantic
from akgm_n0.learner import (
    StateWindowExecutor,
    StateWindowOpcodeInducer,
    StateWindowProgram,
)
from akgm_n0.learner.metamachine_gen2 import REGISTERED_OPCODES


ROOT = Path(__file__).resolve().parents[1]


def hidden_relation(row):
    c, n, a, e, b, d = (int(value) for value in row)
    state = [a, b, c, d, e]
    for _ in range(n):
        state = state[1:] + [sum(state)]
    return float(state[0])


class StateWindowInventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "reports/data/state_window_operator_latest.json").read_text(
                encoding="utf-8"
            )
        )

    def test_semantic_is_reinduced_from_proven_word_code_without_labels(self) -> None:
        room = UniversalFormulaRoom(
            ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
        )
        sources = [
            (record.room_record_id, tuple(record.program["words"]))
            for record in room.records
            if "words" in record.program
        ]
        semantic = StateWindowOpcodeInducer().induce(sources, occupied_opcodes=(16,))
        self.assertEqual(semantic.semantic_id, self.report["invented_operator"]["semantic_id"])
        self.assertEqual(semantic.opcode, 17)
        self.assertNotIn(semantic.opcode, REGISTERED_OPCODES)
        self.assertEqual(semantic.observed_widths, (2, 3, 4))
        verification = verify_state_window_semantic(semantic)
        self.assertTrue(verification["passed"])
        self.assertEqual(sum(item["passed"] for item in verification["obligations"]), 6)

    def test_unseen_width_five_program_replays_sealed_cases(self) -> None:
        report = self.report
        self.assertTrue(all(gate["passed"] for gate in report["gates"]))
        self.assertEqual(report["demonstration"]["unseen_window_width"], 5)
        self.assertEqual(report["experiment"]["self_selected_query_count"], 3)
        self.assertEqual(len(report["mistake_ids"]), 10)
        program = StateWindowProgram.from_dict(
            report["demonstration"]["candidate"]["program"]
        )
        self.assertIn(17, program.words[::2])
        executor = StateWindowExecutor()
        for item in report["sealed_results"]:
            row = tuple(item["inputs"])
            self.assertEqual(executor.execute(program, row).output_value, hidden_relation(row))


if __name__ == "__main__":
    unittest.main()
