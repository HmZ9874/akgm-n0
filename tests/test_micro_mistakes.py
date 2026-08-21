from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import MicroMistakeLibrary, MicroMistakeLibraryError
from akgm_n0.learner import (
    MicroHaltCondition,
    MicroProgram,
    MicroValueNode,
)


def program() -> MicroProgram:
    zero = MicroValueNode("m_constant", constant=0)
    input_0 = MicroValueNode("m_input", index=0)
    input_1 = MicroValueNode("m_input", index=1)
    register_0 = MicroValueNode("m_register", index=0)
    register_1 = MicroValueNode("m_register", index=1)
    return MicroProgram(
        initial_registers=(zero, input_1),
        halt_condition=MicroHaltCondition(1, 0),
        updates=(
            MicroValueNode("m_add", (register_0, input_0)),
            MicroValueNode(
                "m_add",
                (register_1, MicroValueNode("m_constant", constant=-1)),
            ),
        ),
        output_register=0,
    )


class MicroMistakeLibraryTests(unittest.TestCase):
    def test_record_is_idempotent_and_gate_blocks_program(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            library = MicroMistakeLibrary(
                Path(temporary_directory) / "mistakes.jsonl",
                clock=lambda: datetime(2026, 8, 17, tzinfo=timezone.utc),
            )
            arguments = {
                "failed_scope": "blind_zero_control",
                "condition_key": "grid-v1",
                "counterexamples": ({"row": [11, 0], "reason": "nonhalting"},),
                "source_candidate_id": "MC-test",
            }
            first = library.record(program(), **arguments)
            second = library.record(program(), **arguments)
            gate = library.candidate_gate(
                failed_scope="blind_zero_control", condition_key="grid-v1"
            )

            self.assertEqual(first.mistake_id, second.mistake_id)
            self.assertFalse(gate(program()))
            self.assertEqual(len(library.records), 1)

    def test_hash_chain_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "mistakes.jsonl"
            library = MicroMistakeLibrary(path)
            library.record(
                program(),
                failed_scope="blind_zero_control",
                condition_key="grid-v1",
                counterexamples=({"reason": "nonhalting"},),
                source_candidate_id="MC-test",
            )
            event = json.loads(path.read_text(encoding="utf-8"))
            event["condition_key"] = "tampered"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")

            with self.assertRaises(MicroMistakeLibraryError):
                MicroMistakeLibrary(path)


if __name__ == "__main__":
    unittest.main()
