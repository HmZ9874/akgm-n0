from __future__ import annotations

import unittest
import json
from pathlib import Path

from akgm_n0.evaluator import (
    UniversalFormulaCertificate,
    UniversalFormulaRoom,
    UniversalProofVerifier,
)
from akgm_n0.learner import (
    CounterexampleGuidedReflectiveSearch,
    ReflectiveProgram,
    SemanticExtendedExecutor,
    SemanticExtendedProgram,
    SemanticInventionSearch,
    SemanticOpcodeInducer,
)


ROOT = Path(__file__).resolve().parents[1]


def weighted_fourth(a, b, c, d, p, q, r, s, n):
    for _ in range(n):
        a, b, c, d = b, c, d, p * d + q * c + r * b + s * a
    return a


class SemanticInventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        room = UniversalFormulaRoom(
            ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
        )
        cls.sources = tuple(
            (record.room_record_id, ReflectiveProgram.from_dict(dict(record.program)))
            for record in room.records
            if record.program.get("substrate") == "anonymous_unified_word_machine_v0.1"
        )

    def test_induces_first_unused_opcode_from_repeated_proven_microcode(self) -> None:
        semantic = SemanticOpcodeInducer().induce(self.sources)
        self.assertEqual(semantic.opcode, 16)
        self.assertGreaterEqual(semantic.supporting_occurrence_count, 3)
        self.assertEqual(semantic.compression_saving_per_use, 10)
        self.assertTrue(semantic.source_record_ids)

    def test_invented_semantic_crosses_old_instruction_limit(self) -> None:
        semantic = SemanticOpcodeInducer().induce(self.sources)
        executor = SemanticExtendedExecutor(maximum_steps=500_000)
        search = SemanticInventionSearch(semantic, executor=executor)
        rows = (
            (1, 2, 3, 4, 1, 1, 1, 1, 0),
            (4, 5, 6, 7, 2, 1, 3, 1, 0),
            (1, 2, 3, 4, 1, 1, 1, 1, 1),
            (1, 2, 3, 4, 1, 1, 1, 1, 3),
            (1, 2, 3, 4, 1, 1, 1, 1, 6),
            (2, 3, 5, 7, 2, 1, 1, 1, 4),
            (3, 1, 4, 2, 1, 2, 3, 1, 4),
            (5, 2, 1, 6, 3, 1, 2, 4, 3),
        )
        result = CounterexampleGuidedReflectiveSearch(
            search=search, maximum_rounds=12
        ).synthesize(
            opaque_task_id="anonymous-nine-column-semantic-invention",
            input_rows=rows,
            output_values=tuple(weighted_fourth(*row) for row in rows),
            initial_case_indices=(0, 1),
        )
        self.assertTrue(result.converged)
        self.assertGreater(len(result.rounds), 1)
        program = result.final_candidate.program
        self.assertEqual(program.instruction_count, 34)
        self.assertIn(semantic.opcode, program.words[::2])
        self.assertGreater(34 + 4 * semantic.compression_saving_per_use, 64)
        sealed = (
            (6, 9, 2, 5, 4, 2, 3, 1, 3),
            (2, 5, 8, 3, 3, 4, 2, 5, 4),
            (8, 1, 7, 4, 5, 2, 1, 3, 2),
        )
        for row in rows + sealed:
            self.assertEqual(
                executor.execute(program, row).output_value,
                weighted_fourth(*row),
            )

    def test_invented_semantic_and_formula_proof_replay(self) -> None:
        report = json.loads(
            (ROOT / "reports/data/semantic_invention_proof_latest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["strict_formula_total_after"], 33)
        self.assertEqual(report["room_proof_obligation_count"], 467)
        self.assertEqual(report["room_proof_obligation_passed_count"], 467)
        self.assertTrue(report["discovery_summary"]["crossed_old_instruction_limit"])
        room = UniversalFormulaRoom(
            ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
        )
        self.assertEqual(len(room.records), 34)
        record_id = report["strict_room_record"]["room_record_id"]
        record = next(item for item in room.records if item.room_record_id == record_id)
        program = SemanticExtendedProgram.from_dict(dict(record.program))
        certificate = UniversalFormulaCertificate.from_dict(record.certificate)
        replay = UniversalProofVerifier().verify(program, certificate)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.to_dict(), record.verification)


if __name__ == "__main__":
    unittest.main()
