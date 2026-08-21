from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    FormulaSuccessRoom,
    UniversalFormulaCertificate,
    UniversalFormulaRoom,
    UniversalProofVerifier,
    program_digest,
)
from akgm_n0.learner import ReflectiveExecutor, ReflectiveProgram


class ParametricPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.discovery = json.loads(
            (PROJECT_ROOT / "reports" / "data" / "parametric_power_discovery_latest.json").read_text(
                encoding="utf-8"
            )
        )
        cls.proof_report = json.loads(
            (PROJECT_ROOT / "reports" / "data" / "parametric_power_proof_latest.json").read_text(
                encoding="utf-8"
            )
        )
        source_id = cls.discovery["success_room_record"]["room_record_id"]
        source_room = FormulaSuccessRoom(
            PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl"
        )
        cls.source = next(record for record in source_room.records if record.room_record_id == source_id)
        cls.program = ReflectiveProgram.from_dict(dict(cls.source.definition))

    def certificate(self, program):
        verifier = UniversalProofVerifier()
        kind = "natural_parameterized_power"
        return UniversalFormulaCertificate(
            theorem_kind=kind,
            source_room_record_id=self.source.room_record_id,
            source_operation_id=self.source.operation_id,
            program_digest=program_digest(program),
            domain=verifier.DOMAINS[kind],
            claimed_statement=verifier.STATEMENTS[kind],
            claimed_invariants=verifier.INVARIANTS[kind],
            claimed_termination_measure=verifier.TERMINATION[kind],
        )

    def test_counterexample_forces_transition_from_fixed_to_free_base(self) -> None:
        rounds = self.discovery["cegis_rounds"]
        self.assertEqual(len(rounds), 2)
        self.assertEqual(rounds[0]["added_counterexample_index"], 3)
        first_words = rounds[0]["candidate"]["program"]["words"]
        final_words = rounds[1]["candidate"]["program"]["words"]
        first_inputs = {operand for opcode, operand in zip(first_words[::2], first_words[1::2]) if opcode in (1, 5, 6)}
        final_inputs = {operand for opcode, operand in zip(final_words[::2], final_words[1::2]) if opcode in (1, 5, 6)}
        self.assertEqual(first_inputs, {1})
        self.assertEqual(final_inputs, {0, 1})

    def test_one_program_transfers_to_unseen_runtime_bases(self) -> None:
        executor = ReflectiveExecutor(maximum_steps=100_000)
        for base, exponent in ((5, 4), (7, 3), (8, 4), (11, 3), (0, 0), (0, 5)):
            with self.subTest(base=base, exponent=exponent):
                self.assertEqual(
                    executor.execute(self.program, (base, exponent)).output_value,
                    base**exponent,
                )

    def test_parametric_universal_proof_and_room_replay(self) -> None:
        verification = UniversalProofVerifier().verify(self.program, self.certificate(self.program))
        self.assertTrue(verification.passed)
        self.assertEqual(len(verification.obligations), 17)
        room = UniversalFormulaRoom(
            PROJECT_ROOT / "artifacts" / "formula_rooms" / "parametric" / "proven_formulas.jsonl"
        )
        power_records = [
            record for record in room.records
            if record.theorem_kind == "natural_parameterized_power"
        ]
        self.assertEqual(len(power_records), 1)

    def test_fixed_base_mutation_fails_structural_proof(self) -> None:
        words = list(self.program.words)
        add_input_operand_index = next(
            index + 1 for index in range(0, len(words), 2) if words[index] == 5
        )
        words[add_input_operand_index] = 1
        mutated = ReflectiveProgram(tuple(words))
        verification = UniversalProofVerifier().verify(mutated, self.certificate(mutated))
        self.assertFalse(verification.passed)
        failed = {item.obligation_id for item in verification.obligations if not item.passed}
        self.assertIn("exact_program_structure", failed)
        self.assertIn("both_runtime_inputs_are_free", failed)


if __name__ == "__main__":
    unittest.main()
