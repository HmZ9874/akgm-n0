from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    DOMAIN_NATURAL,
    FormulaSuccessRoom,
    UniversalFormulaCertificate,
    UniversalFormulaRoom,
    UniversalProofError,
    UniversalProofVerifier,
    program_digest,
)
from akgm_n0.learner import CompositionGraphProgram, ReflectiveProgram


SOURCES = {
    "natural_power_two": "SF-6e5151b34c144dea",
    "natural_quadratic_plus_linear": "SF-2146c70e3a21cbe4",
    "natural_third_binomial": "SF-5ec3065eebeaea17",
    "natural_modulo_four": "SF-941858d5d23048fc",
    "natural_floor_sqrt": "SF-c5876d5779920c09",
    "natural_square_self_modifying": "SF-48fbc785c0f13cdd",
    "natural_fourth_binomial": "SF-80b3eb3c75fb6348",
    "natural_tribonacci": "SF-29f6d49e09e062c1",
    "natural_bit_length": "SF-b30f3e5d2d2ed251",
    "natural_integer_quotient": "SF-c432c82175c92edb",
    "batch20_t00": "SF-9e5b78eda04c9b43",
    "batch20_t01": "SF-a54cf540bd7351af",
    "batch20_t02": "SF-c5cad01c1d9552db",
    "batch20_t03": "SF-36da9e8f908181d6",
    "batch20_t04": "SF-ba43237f21a13377",
    "batch20_t05": "SF-abb492d332136e2d",
    "batch20_t06": "SF-4b3386bd038cedfa",
    "batch20_t07": "SF-58ad33a5a43c1eba",
    "batch20_t08": "SF-3f2298ace3aedc27",
    "batch20_t09": "SF-d92b3044e542697d",
    "batch20_t10": "SF-b51e4cd3943c102e",
    "batch20_t11": "SF-82178de04d7bcec9",
    "batch20_t12": "SF-fe628c51b2b434bc",
    "batch20_t13": "SF-0df1f1f08dea8c41",
    "batch20_t14": "SF-c991a2802cd4a524",
    "batch20_t15": "SF-f95e1e899ae4e35e",
    "batch20_t16": "SF-fa3e617cf6db2f86",
    "batch20_t17": "SF-f3c6a17f313601d0",
    "batch20_t18": "SF-086f108614466d68",
    "batch20_t19": "SF-292fac498b7a70a1",
    "composition20_c00": "SF-d7edafa5b0195dcc", "composition20_c01": "SF-cff92ec58f8651bf",
    "composition20_c02": "SF-1372d64f867a11e8", "composition20_c03": "SF-866198e7f386a7af",
    "composition20_c04": "SF-ed1fd598f243de2c", "composition20_c05": "SF-17b690870e61b7a7",
    "composition20_c06": "SF-40a4a7eb866e6a72", "composition20_c07": "SF-db3808c4bac7d886",
    "composition20_c08": "SF-fa3a6b769da01a2f", "composition20_c09": "SF-42e3f1b799fcfc1c",
    "composition20_c10": "SF-f67ad91282ccb687", "composition20_c11": "SF-c196b81f2a662ed5",
    "composition20_c12": "SF-0ec51550a00878bb", "composition20_c13": "SF-f02bc9c5b6859759",
    "composition20_c14": "SF-6ab1f083c4370ad0", "composition20_c15": "SF-51e37541bd31921b",
    "composition20_c16": "SF-7b3ade8b358cd481", "composition20_c17": "SF-e0f684a1ddcb08a9",
    "composition20_c18": "SF-dce78a90cfb1695a", "composition20_c19": "SF-39eb835ff81c7065",
}


def source_record(theorem_kind: str):
    room = FormulaSuccessRoom(
        PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl"
    )
    return next(item for item in room.records if item.room_record_id == SOURCES[theorem_kind])


def certificate(theorem_kind: str, program: ReflectiveProgram) -> UniversalFormulaCertificate:
    record = source_record(theorem_kind)
    verifier = UniversalProofVerifier()
    return UniversalFormulaCertificate(
        theorem_kind=theorem_kind,
        source_room_record_id=record.room_record_id,
        source_operation_id=record.operation_id,
        program_digest=program_digest(program),
        domain=verifier.DOMAINS[theorem_kind],
        claimed_statement=verifier.STATEMENTS[theorem_kind],
        claimed_invariants=verifier.INVARIANTS[theorem_kind],
        claimed_termination_measure=verifier.TERMINATION[theorem_kind],
    )


def program_for(theorem_kind: str) -> ReflectiveProgram:
    definition = dict(source_record(theorem_kind).definition)
    if definition.get("substrate") == "anonymous_verified_composition_graph_v0.1":
        return CompositionGraphProgram.from_dict(definition)
    return ReflectiveProgram.from_dict(definition)


class UniversalProofTests(unittest.TestCase):
    def test_fifty_distinct_programs_have_reproducible_universal_proofs(self) -> None:
        verifier = UniversalProofVerifier()
        for theorem_kind in SOURCES:
            with self.subTest(theorem_kind=theorem_kind):
                program = program_for(theorem_kind)
                verification = verifier.verify(program, certificate(theorem_kind, program))
                self.assertTrue(verification.passed)
                self.assertGreaterEqual(len(verification.obligations), 10)
                self.assertTrue(all(item.passed for item in verification.obligations))

    def test_program_mutation_breaks_digest_and_structural_proof(self) -> None:
        program = program_for("natural_power_two")
        original_certificate = certificate("natural_power_two", program)
        words = list(program.words)
        words[17] = 34
        changed = ReflectiveProgram(tuple(words))
        verification = UniversalProofVerifier().verify(changed, original_certificate)
        self.assertFalse(verification.passed)
        failed = {item.obligation_id for item in verification.obligations if not item.passed}
        self.assertIn("program_digest_binding", failed)
        self.assertIn("exact_program_structure", failed)

    def test_wrong_theorem_rule_is_rejected(self) -> None:
        program = program_for("natural_power_two")
        wrong = certificate("natural_modulo_four", program)
        verification = UniversalProofVerifier().verify(program, wrong)
        self.assertFalse(verification.passed)
        self.assertFalse(next(item for item in verification.obligations
                              if item.obligation_id == "exact_program_structure").passed)

    def test_universal_room_reverifies_and_is_idempotent(self) -> None:
        program = program_for("natural_floor_sqrt")
        proof_certificate = certificate("natural_floor_sqrt", program)
        verification = UniversalProofVerifier().verify(program, proof_certificate)
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "proven.jsonl"
            room = UniversalFormulaRoom(path)
            first = room.record(program, proof_certificate, verification)
            second = room.record(program, proof_certificate, verification)
            self.assertEqual(first, second)
            self.assertEqual(len(room.records), 1)
            self.assertEqual(UniversalFormulaRoom(path).records, room.records)

    def test_universal_room_rejects_forged_and_tampered_proofs(self) -> None:
        program = program_for("natural_floor_sqrt")
        proof_certificate = certificate("natural_floor_sqrt", program)
        verification = UniversalProofVerifier().verify(program, proof_certificate)
        forged = type(verification)(
            theorem_kind=verification.theorem_kind,
            passed=True,
            recomputed_statement="false statement",
            obligations=verification.obligations,
            certificate_digest=verification.certificate_digest,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "proven.jsonl"
            room = UniversalFormulaRoom(path)
            with self.assertRaises(UniversalProofError):
                room.record(program, proof_certificate, forged)
            room.record(program, proof_certificate, verification)
            event = json.loads(path.read_text(encoding="utf-8"))
            event["theorem_statement"] = "tampered"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaises(UniversalProofError):
                UniversalFormulaRoom(path)

    def test_composition_cannot_precede_its_component_proofs(self) -> None:
        program = program_for("composition20_c00")
        proof_certificate = certificate("composition20_c00", program)
        verification = UniversalProofVerifier().verify(program, proof_certificate)
        self.assertTrue(verification.passed)
        with tempfile.TemporaryDirectory() as temporary_directory:
            empty_room = UniversalFormulaRoom(Path(temporary_directory) / "proven.jsonl")
            with self.assertRaisesRegex(UniversalProofError, "component not already proven"):
                empty_room.record(program, proof_certificate, verification)


if __name__ == "__main__":
    unittest.main()
