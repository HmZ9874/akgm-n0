from __future__ import annotations

import unittest
import json
from pathlib import Path

from akgm_n0.evaluator import UniversalFormulaRoom
from akgm_n0.evaluator import UniversalFormulaCertificate, UniversalProofVerifier
from akgm_n0.learner import (
    CounterexampleGuidedReflectiveSearch,
    MotifExtractor,
    MotifGrowthSearch,
    ReflectiveExecutor,
    ReflectiveProgram,
)
from akgm_n0.learner.metamachine_gen2 import OP_ADD_INPUT, OP_LOAD_INPUT, OP_SUB_INPUT


ROOT = Path(__file__).resolve().parents[1]


def weighted(a: int, b: int, p: int, q: int, n: int) -> int:
    for _ in range(n):
        a, b = b, p * b + q * a
    return a


class MotifGrowthTests(unittest.TestCase):
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

    def test_extracts_reusable_motifs_from_programs_without_formula_labels(self) -> None:
        motifs = MotifExtractor().extract(self.sources)
        kinds = {motif.kind for motif in motifs}
        self.assertTrue(MotifGrowthSearch.REQUIRED_MOTIFS.issubset(kinds))
        self.assertTrue(all(motif.source_record_ids for motif in motifs))
        self.assertTrue(
            all(motif.structural_signature["derived_from_word_code_only"] for motif in motifs)
        )

    def test_cegis_grows_weighted_second_order_recurrence(self) -> None:
        motifs = MotifExtractor().extract(self.sources)
        executor = ReflectiveExecutor(maximum_steps=200_000)
        search = MotifGrowthSearch(motifs, executor=executor)
        rows = (
            (1, 2, 1, 1, 0),
            (3, 4, 2, 1, 0),
            (1, 2, 1, 1, 1),
            (1, 2, 1, 1, 5),
            (2, 3, 2, 1, 2),
            (2, 3, 2, 1, 4),
            (3, 1, 1, 2, 3),
            (4, 2, 3, 1, 3),
            (5, 3, 2, 2, 4),
            (7, 1, 1, 3, 5),
        )
        report = CounterexampleGuidedReflectiveSearch(
            search=search, maximum_rounds=12
        ).synthesize(
            opaque_task_id="anonymous-five-column-motif-growth",
            input_rows=rows,
            output_values=tuple(weighted(*row) for row in rows),
            initial_case_indices=(0, 1),
        )
        self.assertTrue(report.converged)
        self.assertGreater(len(report.rounds), 1)
        for row in rows + ((6, 9, 4, 2, 3), (2, 5, 3, 4, 4), (8, 1, 5, 2, 2)):
            self.assertEqual(
                executor.execute(report.final_candidate.program, row).output_value,
                weighted(*row),
            )
        instructions = tuple(
            zip(
                report.final_candidate.program.words[::2],
                report.final_candidate.program.words[1::2],
            )
        )
        runtime_inputs = {
            operand
            for opcode, operand in instructions
            if opcode in (OP_LOAD_INPUT, OP_ADD_INPUT, OP_SUB_INPUT)
        }
        self.assertEqual(runtime_inputs, {0, 1, 2, 3, 4})

    def test_latest_discovery_is_universally_proven_and_replayable(self) -> None:
        report = json.loads(
            (ROOT / "reports/data/motif_growth_proof_latest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["strict_formula_total_after"], 31)
        self.assertEqual(report["room_proof_obligation_count"], 424)
        self.assertEqual(report["room_proof_obligation_passed_count"], 424)
        room = UniversalFormulaRoom(
            ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
        )
        self.assertGreaterEqual(len(room.records), 31)
        record_id = report["strict_room_record"]["room_record_id"]
        record = next(item for item in room.records if item.room_record_id == record_id)
        program = ReflectiveProgram.from_dict(dict(record.program))
        certificate = UniversalFormulaCertificate.from_dict(record.certificate)
        replay = UniversalProofVerifier().verify(program, certificate)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.to_dict(), record.verification)


if __name__ == "__main__":
    unittest.main()
