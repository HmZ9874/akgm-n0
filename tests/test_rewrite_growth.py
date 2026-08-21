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
    MotifExtractor,
    ReflectiveExecutor,
    ReflectiveProgram,
    RewriteGrowthSearch,
    RewriteRuleInducer,
)


ROOT = Path(__file__).resolve().parents[1]


def weighted_third(a: int, b: int, c: int, p: int, q: int, r: int, n: int) -> int:
    for _ in range(n):
        a, b, c = b, c, p * c + q * b + r * a
    return a


def load_reflective(room: UniversalFormulaRoom):
    result = []
    for record in room.records:
        if record.program.get("substrate") == "anonymous_unified_word_machine_v0.1":
            result.append(
                (record.room_record_id, ReflectiveProgram.from_dict(dict(record.program)))
            )
    return tuple(result)


class RewriteGrowthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        universal = UniversalFormulaRoom(
            ROOT / "artifacts/formula_rooms/universal/proven_formulas.jsonl"
        )
        strict = UniversalFormulaRoom(
            ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
        )
        cls.universal_sources = load_reflective(universal)
        cls.strict_sources = load_reflective(strict)
        motif_report = json.loads(
            (ROOT / "reports/data/motif_growth_proof_latest.json").read_text(
                encoding="utf-8"
            )
        )
        weighted_id = motif_report["strict_room_record"]["room_record_id"]
        cls.weighted_source = next(
            item for item in cls.strict_sources if item[0] == weighted_id
        )
        cls.motifs = MotifExtractor().extract(cls.strict_sources)

    def test_induces_order_extension_from_program_structure_only(self) -> None:
        rule = RewriteRuleInducer().induce(
            self.universal_sources, self.weighted_source, self.motifs
        )
        self.assertEqual(rule.observed_copy_chain_widths, (2, 3, 4))
        self.assertEqual(rule.evidence["inferred_width_delta"], 1)
        self.assertFalse(rule.evidence["uses_formula_or_theorem_labels"])
        self.assertIn("duplicate_counted_accumulation_term", rule.edit_sequence)

    def test_rewrite_rule_grows_exact_third_order_program(self) -> None:
        rule = RewriteRuleInducer().induce(
            self.universal_sources, self.weighted_source, self.motifs
        )
        executor = ReflectiveExecutor(maximum_steps=300_000)
        search = RewriteGrowthSearch(rule, executor=executor)
        rows = (
            (1, 2, 3, 1, 1, 1, 0),
            (4, 5, 6, 2, 1, 3, 0),
            (1, 2, 3, 1, 1, 1, 1),
            (1, 2, 3, 1, 1, 1, 2),
            (1, 2, 3, 1, 1, 1, 5),
            (2, 3, 5, 2, 1, 1, 3),
            (3, 1, 4, 1, 2, 3, 4),
            (5, 2, 1, 3, 1, 2, 3),
            (2, 7, 4, 2, 3, 1, 4),
        )
        result = CounterexampleGuidedReflectiveSearch(
            search=search, maximum_rounds=12
        ).synthesize(
            opaque_task_id="anonymous-seven-column-rewrite-growth",
            input_rows=rows,
            output_values=tuple(weighted_third(*row) for row in rows),
            initial_case_indices=(0, 1),
        )
        self.assertTrue(result.converged)
        self.assertGreater(len(result.rounds), 1)
        self.assertLessEqual(result.final_candidate.program.instruction_count, 64)
        sealed = (
            (6, 9, 2, 4, 2, 3, 3),
            (2, 5, 8, 3, 4, 2, 4),
            (8, 1, 7, 5, 2, 1, 2),
        )
        for row in rows + sealed:
            self.assertEqual(
                executor.execute(result.final_candidate.program, row).output_value,
                weighted_third(*row),
            )

    def test_rewrite_grown_program_has_replayable_universal_proof(self) -> None:
        report = json.loads(
            (ROOT / "reports/data/rewrite_growth_proof_latest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["strict_formula_total_after"], 32)
        self.assertEqual(report["room_proof_obligation_count"], 444)
        self.assertEqual(report["room_proof_obligation_passed_count"], 444)
        room = UniversalFormulaRoom(
            ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
        )
        self.assertGreaterEqual(len(room.records), 32)
        record_id = report["strict_room_record"]["room_record_id"]
        record = next(item for item in room.records if item.room_record_id == record_id)
        program = ReflectiveProgram.from_dict(dict(record.program))
        certificate = UniversalFormulaCertificate.from_dict(record.certificate)
        replay = UniversalProofVerifier().verify(program, certificate)
        self.assertTrue(replay.passed)
        self.assertEqual(replay.to_dict(), record.verification)


if __name__ == "__main__":
    unittest.main()
