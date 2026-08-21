"""Prove and admit the discovered two-input parametric program."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
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


def main() -> int:
    discovery = json.loads(
        (PROJECT_ROOT / "reports" / "data" / "parametric_power_discovery_latest.json").read_text(
            encoding="utf-8"
        )
    )
    source_id = discovery["success_room_record"]["room_record_id"]
    bounded_room = FormulaSuccessRoom(
        PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl"
    )
    source = next(record for record in bounded_room.records if record.room_record_id == source_id)
    program = ReflectiveProgram.from_dict(dict(source.definition))
    verifier = UniversalProofVerifier()
    theorem_kind = "natural_parameterized_power"
    certificate = UniversalFormulaCertificate(
        theorem_kind=theorem_kind,
        source_room_record_id=source.room_record_id,
        source_operation_id=source.operation_id,
        program_digest=program_digest(program),
        domain=verifier.DOMAINS[theorem_kind],
        claimed_statement=verifier.STATEMENTS[theorem_kind],
        claimed_invariants=verifier.INVARIANTS[theorem_kind],
        claimed_termination_measure=verifier.TERMINATION[theorem_kind],
    )
    verification = verifier.verify(program, certificate)
    if not verification.passed:
        print(json.dumps(verification.to_dict(), ensure_ascii=False, indent=2))
        return 1
    room = UniversalFormulaRoom(
        PROJECT_ROOT / "artifacts" / "formula_rooms" / "parametric" / "proven_formulas.jsonl"
    )
    record = room.record(program, certificate, verification)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-parametric-power-proof-{stamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    obligations = verification.obligations
    first_round = discovery["cegis_rounds"][0]
    counterexample_index = first_round["added_counterexample_index"]
    counterexample_final = discovery["development_results"][counterexample_index]
    first_program = ReflectiveProgram.from_dict(first_round["candidate"]["program"])
    first_prediction = ReflectiveExecutor(maximum_steps=100_000).execute(
        first_program, tuple(counterexample_final["inputs"])
    ).output_value
    report = {
        "report_version": "strict-parametric-formula-proof-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "首个严格参数化公式证明",
        "verdict": "strict_parametric_formula_proven",
        "formula": "F(a,n)=a^n",
        "domain": "a,n in N; 0^0=1",
        "source_discovery_run_id": discovery["run_id"],
        "candidate_id": discovery["candidate"]["candidate_id"],
        "source_room_record_id": source.room_record_id,
        "source_operation_id": source.operation_id,
        "parametric_room_record_id": record.room_record_id,
        "strict_parametric_formula_count": len(room.records),
        "classification_correction": {
            "fixed_base_instances": ["2^n", "3^n"],
            "fixed_base_instances_count_as_new_parametric_formulas": False,
            "derived_composition_examples_count_as_new_parametric_formulas": False,
            "required_free_runtime_inputs": ["a", "n"],
        },
        "discovery_trace": {
            "cegis_round_count": len(discovery["cegis_rounds"]),
            "first_round_was_fixed_base_instance": True,
            "counterexample_that_forced_abstraction": {
                "inputs": counterexample_final["inputs"],
                "predicted": first_prediction,
                "observed": counterexample_final["observed"],
            },
            "unseen_bases": sorted({item["inputs"][0] for item in discovery["sealed_results"]}),
            "unseen_cases_passed": sum(item["passed"] for item in discovery["sealed_results"]),
            "unseen_case_count": len(discovery["sealed_results"]),
        },
        "program": program.to_dict(),
        "proof": verification.to_dict(),
        "proof_obligation_count": len(obligations),
        "proof_obligation_passed_count": sum(item.passed for item in obligations),
        "invariants": list(certificate.claimed_invariants),
        "termination_measure": certificate.claimed_termination_measure,
        "learner_received": discovery["learner_received"],
        "autonomy_boundary": {
            "learner_selected": "two-input nested state transfer, runtime base use, runtime exponent use, update direction and halt path",
            "host_supplied": "generic nested-counter grammar, addition/subtraction VM semantics, anonymous numeric evidence and resource bounds",
            "posthoc_only": "the symbols a^n, exponent terminology and proof theorem name",
        },
        "limitations": discovery["limitations"],
    }
    artifact = run_directory / "parametric_power_proof_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        PROJECT_ROOT / "reports" / "data" / "parametric_power_proof_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "parametric_power_proof_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id, "verdict": report["verdict"], "formula": report["formula"],
        "parametric_room_record": record.room_record_id,
        "obligations": len(obligations), "passed": report["proof_obligation_passed_count"],
        "artifact_path": str(artifact.relative_to(PROJECT_ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
